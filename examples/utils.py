import os
import subprocess


def launch_process(*args):
    return subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)


def collect_process_output(process, filename):
    output = process.communicate()[0].decode('utf8')

    if process.returncode == 0:
        with open(filename, 'w') as result_file:
            result_file.write(output)
    else:
        raise RuntimeError(
            "%s exit code %d, output:\n%s"
            % (' '.join(process.args), process.returncode, output))


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path)
        except EnvironmentError:  # another hook created the same folder
            pass
