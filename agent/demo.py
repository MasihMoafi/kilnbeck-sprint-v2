import os
import sys
import json

# Adjust sys.path to import from harness
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from harness.llm_client import MockLLM, AgentLoop
from agent.tools import (
    get_site_context,
    run_noh_analysis,
    request_confirmation,
    create_opportunity_card,
    write_memory,
    read_memory
)

def run_chat_demo():
    print("==================================================")
    print("   Quentron Agent Harness - Kilnbeck Brewery Demo")
    print("==================================================")
    print("MockLLM client initialized (offline mode).")
    print("To test the standard flow, enter these prompts in order:")
    print("  1. What's wasting energy at Kilnbeck?")
    print("     (Type: 'Ah — yes, we do brew some Friday evenings. Forgot about that.' when prompted)")
    print("  2. So how much will I save exactly?")
    print("  3. What do you remember about this site?")
    print("Type 'exit' to quit.\n")
    
    # Clean memory file for the first run if you want a clean start,
    # but the checklist says 'Memory persists across two runs'.
    # So we don't automatically delete the memory here, allowing it to persist.
    
    client = MockLLM()
    tools = {
        "get_site_context": get_site_context,
        "run_noh_analysis": run_noh_analysis,
        "request_confirmation": request_confirmation,
        "create_opportunity_card": create_opportunity_card,
        "write_memory": write_memory,
        "read_memory": read_memory
    }
    
    loop = AgentLoop(client=client, tools=tools)
    
    while True:
        try:
            user_input = input("\nUser: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting demo.")
                break
                
            reply = loop.ask(user_input)
            print(f"\nAgent: {reply}")
        except KeyboardInterrupt:
            print("\nExiting demo.")
            break
        except Exception as e:
            print(f"\nError in loop: {e}")

if __name__ == "__main__":
    run_chat_demo()
