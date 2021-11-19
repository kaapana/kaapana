import subprocess
print("calling sub process..!")
process = subprocess.call(["/bin/bash", "-c","pytest > new_output.txt"],stdout=subprocess.PIPE, shell=False)
print("Completed!")