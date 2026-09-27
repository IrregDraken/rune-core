from __future__ import annotations
import argparse
from .adapters.ollama import OllamaModel
from .runtime import RUNERuntime

def main()->None:
    parser=argparse.ArgumentParser(description="RUNE local runtime")
    parser.add_argument("--model",default="llama3.2:3b")
    parser.add_argument("--db",default="data/rune.db")
    args=parser.parse_args()
    runtime=RUNERuntime(OllamaModel(model=args.model),db_path=args.db)
    print("RUNE online. Type 'exit' to stop.")
    try:
        while True:
            text=input("You > ").strip()
            if text.lower() in {"exit","quit"}: break
            if text: print(f"RUNE > {runtime.receive(text)}")
    finally: runtime.close()

if __name__=="__main__": main()
