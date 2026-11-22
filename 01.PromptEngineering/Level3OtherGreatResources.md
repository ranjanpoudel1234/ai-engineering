# Other Excellent Resources from Prompt Engineering Courses

## Claude Cookbook

1. Excellent Example of things like summarization, classification, RAG, evaluation with Claude and more. https://github.com/anthropics/claude-cookbooks/tree/main
2. Also has great prompt examples

## Claude API DOcs
https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations

## Prompting Guide and Best Practices

https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

1. Long Context Prompting - When working with large documents
   1. Put long documents and input data at the top
   2. Structure document content with metadata and xml
   3. Ground response in Quotes
     ```text
        You are an AI physician's assistant. Your task is to help doctors diagnose possible patient illnesses.
            <documents>
            <document index="1">
                <source>patient_symptoms.txt</source>
                <document_content>
                {{PATIENT_SYMPTOMS}}
                </document_content>
            </document>
            <document index="2">
                <source>patient_records.txt</source>
                <document_content>
                {{PATIENT_RECORDS}}
                </document_content>
            </document>
            <document index="3">
                <source>patient01_appt_history.txt</source>
                <document_content>
                {{PATIENT01_APPOINTMENT_HISTORY}}
                </document_content>
            </document>
            </documents>

            Find quotes from the patient records and appointment history that are relevant to diagnosing the patient's reported symptoms. Place these in <quotes> tags. Then, based on these quotes, list all information that would help the doctor diagnose the patient's symptoms. Place your diagnostic information in <info> tags.

     ```

2. Tell it what do to instead of what not to do. Instead of saying "Don't make up sources", say "Only use the following sources to answer the question and quote them in your response: {{SOURCES}}"

## Prompt Template and Prompt Improver

https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-tools

1. You could write a skill that looks at the latest claude knowledge and improves your prompt based on that. For example, if you have a retrieval augmented generation system, you could have a prompt improver that looks at the sources retrieved and then improves the prompt to better use those sources.

## Chaining Prompts

1. Break a big task into multiple steps
2. This helps you to inspect intermediate outputs or enforce a specific pipeline structure.
3. Eg. Self correction: Generate a draft -> Have claude review it against criteria. Have LLM refine based on the review. Each step is separate call
so you can log, evaluate or branch at any point!