import os
import sys
from pathlib import Path
import sys


class SimpleExecution():
    
    def __init__(self):
        print("Init it!")
        print("ok")
        print("Number of argumets: ", len(sys.argv)-1)
        if len(sys.argv) > 3:
            self.output = sys.argv[1]
            self.input = sys.argv[3]
        super().__init__()
  
    def run(self):
        print("input: ", self.input)
        print("output: ", self.output)
        with open(self.output, 'w') as f:
            for idx, x in enumerate(sys.argv):
                if idx < 3:
                    continue
                print("additional output ", idx, ": ", x)
                f.write(" input: "+ self.input + "\n")
                f.write(" output: "+ self.output +"\n")
                f.write(str(" additional output "+ str(idx) + ": "+ x + "\n"))


if __name__ == "__main__":
    simple_execution = SimpleExecution()
    simple_execution.run()