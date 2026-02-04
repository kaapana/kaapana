#!/usr/bin/env python3
"""Update gitlab-runner config.toml with runner settings.

Usage:
  register_runner_settings.py \
    --config /home/ubuntu/.gitlab-runner/config.toml \
    --shared-name shared-foo --shared-limit 5 --shared-request-concurrency 4 \
    --dedicated-name dedicated-foo --dedicated-limit 1 --dedicated-request-concurrency 4 \
    --vm-name foo
"""
import argparse
import sys


def add_runner_settings(content, runner_name, limit, request_concurrency, vm_name):
    lines = content.splitlines()
    new_lines = []
    in_runner = False
    added_settings = False
    for line in lines:
        new_lines.append(line)
        if f'name = "{runner_name}"' in line:
            in_runner = True
        if in_runner and not added_settings:
            if line.strip().startswith('executor ='):
                new_lines.append(f'  limit = {limit}')
                new_lines.append(f'  request_concurrency = {request_concurrency}')
                new_lines.append('  [runners.custom_build_dir]')
                new_lines.append('    enabled = true')
                new_lines.append(f'  environment = ["DEPLOYMENT_INSTANCE_NAME={vm_name}"]')
                added_settings = True
                in_runner = False
    return '\n'.join(new_lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True, help='Path to config.toml')
    p.add_argument('--shared-name', required=True)
    p.add_argument('--shared-limit', type=int, required=True)
    p.add_argument('--shared-request-concurrency', type=int, required=True)
    p.add_argument('--dedicated-name', required=True)
    p.add_argument('--dedicated-limit', type=int, required=True)
    p.add_argument('--dedicated-request-concurrency', type=int, required=True)
    p.add_argument('--vm-name', required=True)
    args = p.parse_args()

    try:
        with open(args.config, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f'ERROR: cannot read config {args.config}: {e}', file=sys.stderr)
        sys.exit(2)

    content = add_runner_settings(content, args.shared_name, args.shared_limit, args.shared_request_concurrency, args.vm_name)
    content = add_runner_settings(content, args.dedicated_name, args.dedicated_limit, args.dedicated_request_concurrency, args.vm_name)

    try:
        with open(args.config, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f'ERROR: cannot write config {args.config}: {e}', file=sys.stderr)
        sys.exit(3)

    print(f'Updated {args.config} with settings for {args.shared_name} and {args.dedicated_name}')


if __name__ == '__main__':
    main()
