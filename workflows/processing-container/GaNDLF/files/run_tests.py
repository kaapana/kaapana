import subprocess
import sys
print("calling sub process..!")
#resp = subprocess.check_output(["/bin/bash", "-c","pytest > new_outputs.txt"], stderr=subprocess.STDOUT)
resp = subprocess.check_output(["/bin/bash", "-c","pytest"], stderr=subprocess.STDOUT)
print(resp)

print("Completed!")