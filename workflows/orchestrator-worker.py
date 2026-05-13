import anthropic
from dotenv import load_dotenv
import os
import re

load_dotenv()
my_api_key = os.getenv("ANTHROPIC_API_KEY")

from util import llm_call, extract_xml


ORCHESTRATOR_PROMPT = """
Analyze this task and break it down into 2-3 distinct approaches:

Task: {task}

Return your response in this format:

<analysis>
Explain your understanding of the task and which variations would be valuable.
Focus on how each approach serves different aspects of the task.
</analysis>

<tasks>
    <task>
    <type>formal</type>
    <description>Write a precise, technical version that emphasizes specifications</description>
    </task>
    <task>
    <type>conversational</type>
    <description>Write an engaging, friendly version that connects with readers</description>
    </task>
</tasks>
"""

WORKER_PROMPT = """
Generate content based on:
Task: {original_task}
Style: {task_type}
Guidelines: {task_description}

Return your response in this format:

<response>
Your content here, maintaining the specified style and fully addressing requirements.
</response>
"""

def parse_tasks(tasks_xml: str) -> list[dict]:
    """Parse XML tasks into a list of task dictionaries."""
    tasks = []
    current_task = {}

    for line in tasks_xml.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("<task>"):
            current_task = {}
        elif line.startswith("<type>"):
            current_task["type"] = line[6:-7].strip()
        elif line.startswith("<description>"):
            current_task["description"] = line[12:-13].strip()
        elif line.startswith("</task>"):
            if "description" in current_task:
                if "type" not in current_task:
                    current_task["type"] = "default"
                tasks.append(current_task)

    return tasks

class FlexibleOrchestrator :
    def __init__(
        self,
        orchestrator_prompt : str,
        worker_prompt : str
    ):
        self.orchestrator_prompt = orchestrator_prompt
        self.worker_prompt = worker_prompt

    def _format_prompt(self,template:str,**kwargs):
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(e)

    def process(self,task:str,context:dict):
        context = context or {}
        orchestrator_input = self._format_prompt(self.orchestrator_prompt,task=task,**context)
        orchestrator_reponse = llm_call(orchestrator_input)

        analysis = extract_xml(orchestrator_reponse,"analysis")
        tasks = extract_xml(orchestrator_reponse,"tasks")
        parsed_tasks = parse_tasks(tasks)
    

        # Process each task
        worker_result = []
        for i, task_info in enumerate(parsed_tasks,1):
            worker_input = self._format_prompt(self.worker_prompt,original_task=task,task_type=task_info['type'],task_description=task_info['description'])

            worker_response = llm_call(worker_input)
            extracted_worker_response = extract_xml(worker_response,"response")
            if not extracted_worker_response or not extracted_worker_response.strip():
                print(f"{i} - {extracted_worker_response}")
                extracted_worker_response = f"failed to generate response"
            worker_result.append({
                "type" : task_info['type'],
                "description" : task_info['description'],
                "content" : extracted_worker_response
            })
            # Display results
            print("\n" + "=" * 80)
            print("RESULTS")
            print("=" * 80)
            for i, result in enumerate(worker_result, 1):
                print(f"\n{'-' * 80}")
                print(f"Approach {i}: {result['type'].upper()}")
                print(f"{'-' * 80}")
                print(f"\n{result['result']}\n")
        return worker_result


orchestrator = FlexibleOrchestrator(
    orchestrator_prompt=ORCHESTRATOR_PROMPT,
    worker_prompt=WORKER_PROMPT,
)

orchestrator.process(
    task="Write a product description for a new eco-friendly water bottle",
    context={
        "target_audience": "environmentally conscious millennials",
        "key_features": ["plastic-free", "insulated", "lifetime warranty"],
    },
)