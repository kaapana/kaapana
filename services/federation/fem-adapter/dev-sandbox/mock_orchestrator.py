#!/usr/bin/env python3
"""
Stands in for the EUCAIM FEM-orchestrator for local testing: publishes a
submit_run command to the real FEM-client container over RabbitMQ using the
exact wire protocol receiver.py expects (pipe-delimited command, chunked
reply-queue response with a sha256 checksum), and prints the final decoded
JSON result.

Run against the sandbox in this directory: `docker compose up -d --build`,
then `python3 mock_orchestrator.py` (needs `pip install pika` on the host).
"""
import base64
import hashlib
import json
import sys
import uuid

import pika

NODE_QUEUE = "kaapana-dev-node"  # must match config/config.py's node_name
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672


def build_submit_run_message(task_id: str, user_id: str, token: str) -> str:
    """
    Builds the pipe-delimited submit_run command receiver.py's on_request()
    parses:
      submit_run|<tool_id>|<task_info>|<execution>|<parametric_args>|<user_id>|<public_ip>|submit_run|<token>
    """
    task_info = {
        "_id": task_id,
        "command": {"base": "echo hello-from-kaapana-fem-adapter", "args": []},
    }
    # task_info must be a Python-literal string (ast.literal_eval'd) --
    # single-quoted, so repr() is exactly right.
    task_info_str = repr(task_info)

    execution = {"execution_id": f"exec-{uuid.uuid4().hex[:8]}", "process_info": []}
    execution_str = json.dumps(execution)

    parametric_args_str = "{}"  # eval()'d by receiver.py

    fields = [
        "submit_run",
        task_id,  # tool_id
        task_info_str,
        execution_str,
        parametric_args_str,
        user_id,
        "None",  # public_ip -- literal "None" becomes Python None on parse
        "submit_run",  # json_action
        token,
    ]
    return "|".join(fields), execution["execution_id"]


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    message, execution_id = build_submit_run_message(
        task_id="kaapana-fem-smoketest", user_id="test-user", token="dev-sandbox-token"
    )
    print(f"[mock-orchestrator] submit_run message for execution_id={execution_id}:")
    print(f"  {message}\n")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials("guest", "guest"),
        )
    )
    channel = connection.channel()

    reply_queue = channel.queue_declare(queue="", exclusive=True).method.queue
    correlation_id = str(uuid.uuid4())

    chunks: dict[int, str] = {}
    expected_total = None
    expected_checksum = None
    result_holder: dict[str, bytes] = {}

    def on_response(ch, method, props, body):
        nonlocal expected_total, expected_checksum
        if props.correlation_id != correlation_id:
            return
        packet = json.loads(body)
        if packet["type"] == "chunk_start":
            expected_total = packet["total"]
            expected_checksum = packet["checksum"]
            print(
                f"[mock-orchestrator] chunk_start: expecting {expected_total} "
                f"chunk(s), checksum={expected_checksum}"
            )
        elif packet["type"] == "chunk":
            chunks[packet["index"]] = packet["data"]
            print(f"[mock-orchestrator] received chunk {packet['index'] + 1}/{expected_total}")
            if expected_total is not None and len(chunks) == expected_total:
                full_b64 = "".join(chunks[i] for i in sorted(chunks))
                raw = base64.b64decode(full_b64)
                actual_checksum = compute_checksum(raw)
                if actual_checksum != expected_checksum:
                    raise RuntimeError(
                        f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                    )
                print("[mock-orchestrator] checksum verified OK")
                result_holder["raw"] = raw
                ch.stop_consuming()

    channel.basic_consume(queue=reply_queue, on_message_callback=on_response, auto_ack=True)

    channel.basic_publish(
        exchange="",
        routing_key=NODE_QUEUE,
        properties=pika.BasicProperties(reply_to=reply_queue, correlation_id=correlation_id),
        body=message.encode("utf-8"),
    )
    print(f"[mock-orchestrator] published to queue '{NODE_QUEUE}', awaiting response...\n")

    channel.connection.call_later(60, channel.stop_consuming)
    channel.start_consuming()
    connection.close()

    if "raw" not in result_holder:
        print("[mock-orchestrator] TIMED OUT waiting for a response", file=sys.stderr)
        return 1

    result = json.loads(result_holder["raw"])
    print("\n[mock-orchestrator] final decoded submit_run result:")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
