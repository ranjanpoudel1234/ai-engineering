# Additional Levels of Prompt Engineering

## 5. Precognition

a. Give Claude time to think
b. Tell it to think
c. Tell it to think out loud.

### Example without thinking provided

User: "User: Is this movie review sentiment positive or negative?

```text
This movie blew my mind with its freshness and originality. In totally unrelated news, I have been living under a rock since the year 1900."
```

AI Response: This is wrong as the review is mixed.

```text
"The sentiment of this movie review is positive.

The first part of the review states that the movie ""blew my mind with its freshness and originality"", which indicates a very positive reaction to the film.

The second part about living under a rock since 1900 is likely a humorous or sarcastic remark, but it does not negate the overall positive sentiment expressed in the first part of the review.

So based on the language used, this can be considered a positive movie review, despite the somewhat tongue-in-cheek final statement."
```

Better Prompt: Tell it to write it thoughts in XML tags.

```text
You are a savvy reader of movie reviews.

User: Is this review sentiment positive or negative? First, **write the best arguments for each side in <positive-argument> and <negative-argument> XML tags, then answer.**

This movie blew my mind with its freshness and originality. In totally unrelated news, I have been living under a rock since 1900.

```

## 6. Using Examples or Few Shot Prompting

a. Tell Claude how you WANT it to behave or how you DO NOT want it to behave by giving it examples or counter examples.

b. Zero Shot, n shot or one shot are other phrases used.

c. You also use other models ahead to create summary and give example of user query and that summary that you liked as example input to final prompt.

### Example: Without Examples provided - Claude will not know how to respond in the way you want it

```text
User: Will Santa bring me presents on Christmas?

Claude: I don't actually have any information about whether Santa will bring you presents on Christmas. Santa Claus is a fictional character, and whether he brings presents or not depends on the beliefs and traditions of each individual family. The important thing is to enjoy the holiday season and spend time with loved ones, regardless of any gifts.

```

### Example: With Examples provided - Claude will understand how to respond in the way you want it

```text
"User: Please complete the conversation by writing the next line, speaking as ""A"".

Q: Is the tooth fairy real?
A: Of course, sweetie. Wrap up your tooth and put it under your pillow tonight. There might be something waiting for you in the morning.
Q: Will Santa bring me presents on Christmas?"

Claude: A: Yes, my dear, as long as you've been good this year, Santa will be sure to bring you presents on Christmas! Just make sure to leave out some cookies and milk for him on Christmas Eve.
```

### Another example with examples provided - Claude will understand how to respond in the way you want it

```text

"User: Please classify the given email in one of the given categories:

<categories>
(A) Pre-sale question
(B) Broken or defective item
(C) Billing question
(D) Other (please explain)
<</categories>

For example: If the email says something like ""This item is broken"", your output should be
just letter B.

You always respond with just letter of category. No other words

Here is the email:  {{EMAIL}}



Assistant:"

```

## 7. Avoiding Hallucinations 

https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations

a. Give LLM options to say it does not know the answer
b. Asking to find evidence before answering
c. Use direct quotes to for factual grounding

Other methods

a. Chain-of-thought verification: Ask the LLM to explain its reasoning step-by-step before giving a final answer. This can reveal faulty logic or assumptions.

b. Best-of-N verification: Run the LLM through the same prompt multiple times and compare the outputs. Inconsistencies across outputs could indicate hallucinations.

c. Iterative refinement: Use the LLM's outputs as inputs for follow-up prompts, asking it to verify or expand on previous statements. This can catch and correct inconsistencies.

d. External knowledge restriction: Explicitly instruct the LLM to only use information from provided documents and not its general knowledge.


Example of Hallucination: Long text given, then asked for specific question. Claude hallucinates.

```text
User: <question>What was Matterport's subscriber base on the precise date of May 31, 2020?</question>

Please read the below document. Then write a brief numerical answer inside <answer> tags.

<document>
{{DOCUMENT}}
</document>

LLM Response:  <answer>503,000</answer> --> This is made up number
```

Solution:
```text
User: <question>What was Matterport's subscriber base on the precise date of May 31, 2020?</question>

Please read the below document. 

Then, in <scratchpad> tags, pull the most relevant quote from the document and consider whether it answers the user's question or whether it lacks sufficient detail. Then write a brief numerical answer in <answer> tags.

<document>
```

Another example: LLM will hallucinate and give a long answer to a question that it does not know the answer to. It will make up information.

```text
User: User: Who is the heaviest hippo of all time?

LLM: "Unfortunately, there doesn't seem to be a definitive record for the heaviest hippo of all time. Hippos are known to be one of the largest land animals, but their exact weights can vary significantly.

Some key points about hippo weights:

- Hippos are sexually dimorphic, meaning male hippos are typically much larger than females. Adult male hippos can weigh between 3,000-9,000 lbs (1,360-4,080 kg), while females are usually 3,000-5,000 lbs (1,360-2,270 kg).

- The largest recorded wild hippo was a male shot in Uganda in 1926, which weighed around 9,920 lbs (4,500 kg). However, this weight is not definitively confirmed.

- In captivity, some exceptionally large hippos have been recorded, such as a male named Ubangi at the San Diego Zoo who weighed around 9,920 lbs (4,500 kg) in the 1970s.

- Overall, the heaviest hippo on record is likely to be an exceptionally large male from the wild, but the exact weight is difficult to confirm definitively. Hippo weights can vary greatly based on factors like age, sex, and habitat conditions.

So in summary, while there are some very large hippos on record, there doesn't seem to be a universally agreed upon ""heaviest hippo of all time"" due to the challenges in accurately measuring and verifying the weights of these massive animals."
```

Solution:

```text
User: Who is the heaviest hippo of all time? Only answer if you know the answer with certainty.

LLM: I do not have definitive information about the heaviest hippo of all time. Hippo weights can vary significantly, and without access to comprehensive records, I cannot state with certainty who the heaviest hippo was. Hippo weights are not as well-documented as some other animals, so I do not want to provide an unverified claim.
```
