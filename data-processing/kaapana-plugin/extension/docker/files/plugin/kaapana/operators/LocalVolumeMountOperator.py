import os, shutil
from kaapana.operators.KaapanaPythonBaseOperator import (
    KaapanaPythonBaseOperator
)


class LocalVolumeMountOperator(KaapanaPythonBaseOperator):
    """
    An operator to apply an action like copy or remove to files in a volume mount.

    Files are copied in a way that the local file path relative to /kaapana/mounted/workflows/data/<run_id>
    is the same as the local file path relative to <mount_path>.

    **Inputs:**
    """

    def __init__(
        self,
        dag,
        mount_path: str,
        action: str,
        whitelisted_file_endings: tuple,
        name: str = None,
        keep_directory_structure: bool = False,
        action_operators: list = None,
        action_files: list = None,
        *args,
        **kwargs,
    ):
        """
        :param mount_path: The path to the mountPath in airflow_scheduler.
        :param action: The action to apply on the files.
        :param name: The name of the task in airflow.
        :param whitelisted_file_endings: Allowed file formats.
        :param keep_directory_structure: If true files copied to the volume mount keep the same local path relative to <mount_path> as their original path relative to /kaapana/mounted/workflows/data/<run_id>.
        :param action_operators: For action <put>: .
        :param action_files: For action <get> and <remove>: List of files in <mount_path> to apply the action on.
        """
        assert action in ["get", "remove", "put"]

        name = name or f"{action}-mounted-files"
        self.mount_path = mount_path
        self.action = action
        self.keep_directory_structure = keep_directory_structure
        self.action_operators = action_operators or []
        self.action_files = action_files or []
        self.whitelisted_file_endings = whitelisted_file_endings or ()

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)

    def start(self, **kwargs):
        conf = kwargs["dag_run"].conf
        data_form = conf.get("data_form", {})
        self.action_files = self.action_files or data_form.get("action_files", [])

        self.init_source_and_destination(**kwargs)
        if self.action in ["put"]:
            processed_files = self.put_to_mountpath()
        elif self.action == "get":
            processed_files = self.copy_from_mount_path()
        elif self.action == "remove":
            processed_files = self.remove_files_from_mount()

        if not len(processed_files):
            raise AssertionError("No files have been processed!")

    def init_source_and_destination(self, **kwargs):
        """
        Set directory of source files and destination files based on action
        This has to be done after super.__init__()
        """
        if self.action in ["get", "remove"]:
            self.source_dir = self.mount_path
            self.destination_dir = os.path.join(
                self.airflow_workflow_dir, kwargs["dag_run"].run_id
            )
        elif self.action in ["put"]:
            self.source_dir = os.path.join(
                self.airflow_workflow_dir, kwargs["dag_run"].run_id, "batch"
            )
            if self.keep_directory_structure:
                self.destination_dir = os.path.join(
                    self.mount_path, kwargs["dag_run"].run_id, "batch"
                )
            else:
                self.destination_dir = self.mount_path

    def copy_file(self, src: str, dst: str):
        """
        Copy files from src to dst.
        If directory for dst does not exist, create the directory recursively.
        """
        target_dir = os.path.dirname(dst)
        if not os.path.isdir(target_dir):
            print(f"Create directory {target_dir}.")
            os.makedirs(target_dir, exist_ok=True)
        try:
            dst_path = shutil.copy2(src=src, dst=dst)
            print(f"Successfully copied {src} to {dst_path}")
        except Exception as e:
            print(f"Failed to copy {src} to {dst}")
            raise e

    def iswhitelisted(self, file_path: str) -> bool:
        """
        Check if filepath ends with a whitelisted file format.
        """
        for file_ending in self.whitelisted_file_endings:
            print(f"{file_ending=}")
            print(f"{file_path=}")
            if file_path.lower().endswith(file_ending):
                return True
        return False

    def put_to_mountpath(self):
        """
        Get a list of local paths to the targeted files relative to self.source_dir
        """
        files_to_act_on = []
        batch_elements = os.listdir(self.source_dir)
        for element in batch_elements:
            for action_operator in self.action_operators:
                for file_path in os.listdir(
                    os.path.join(
                        self.source_dir, element, action_operator.operator_out_dir
                    )
                ):
                    files_to_act_on.append(
                        os.path.join(
                            element,
                            action_operator.operator_out_dir,
                            file_path,
                        )
                    )
        processed_files = []
        for file_path in files_to_act_on:
            if not self.iswhitelisted(file_path):
                print(f"{file_path} is not whitelisted and will be ignored")
                continue
            if not self.keep_directory_structure:
                file_basename = os.path.basename(file_path)
                dst = os.path.join(self.destination_dir, file_basename)
            else:
                dst = os.path.join(self.destination_dir, file_path)
            self.copy_file(
                src=os.path.join(self.source_dir, file_path),
                dst=dst,
            )
            processed_files.append(file_path)
        return processed_files

    def copy_from_mount_path(self):
        """
        Get files from mount_path
        """
        files_in_source_dir = os.listdir(self.source_dir)
        print(f"{files_in_source_dir=}")
        print(f"{self.action_files=}")
        files_to_act_on = [
            f for f in files_in_source_dir if os.path.basename(f) in self.action_files
        ]
        processed_files = []
        for file_path in files_to_act_on:
            if not self.iswhitelisted(file_path):
                print(f"{file_path} is not whitelisted and will be ignored")
                continue
            self.copy_file(
                src=os.path.join(self.source_dir, file_path),
                dst=os.path.join(
                    self.destination_dir, self.operator_out_dir, file_path
                ),
            )
            processed_files.append(file_path)
        return processed_files

    def remove_files_from_mount(self):
        """
        Remove files from the volume mount
        """
        files_in_source_dir = os.listdir(self.source_dir)
        print(f"{files_in_source_dir=}")
        print(f"{self.action_files=}")
        files_to_act_on = [
            f for f in files_in_source_dir if os.path.basename(f) in self.action_files
        ]
        processed_files = []
        for file_path in files_to_act_on:
            if not self.iswhitelisted(file_path):
                print(f"{file_path} is not whitelisted and will be ignored")
                continue
            abs_file_path = os.path.join(self.source_dir, file_path)
            try:
                os.remove(abs_file_path)
                print(f"Successfully removed {abs_file_path} from volume mount.")
                processed_files.append(abs_file_path)
            except Exception as e:
                print(f"Failed to remove {abs_file_path} from volume mount")
                raise e
        return processed_files
