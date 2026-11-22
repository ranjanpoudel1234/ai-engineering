# Learning Journey on Prompt Engineering

## Claudes Prompt Engineering Interactive Tutorial

https://github.com/anthropics/prompt-eng-interactive-tutorial
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
https://developers.openai.com/api/docs/guides/prompt-engineering

https://docs.google.com/spreadsheets/d/1BMTB1HOZH0fyXW1eGLl64l-zbgmc2gGwNONz6VVR2fI/edit?pli=1&gid=257656347#gid=257656347

### 1. Be Clear and Direct:

a. Think of Claude like any other human that is new to the job. Claude has no context on what to do aside from what you literally tell it. Just as when you instruct a human for the first time on a task, the more you explain exactly what you want in a straightforward manner to Claude, the better and more accurate Claude's response will be.

b. When in doubt, follow the Golden Rule of Clear Prompting: show your prompt to a colleague or friend and have them follow the instructions themselves to see if they can produce the result you want. If they're confused, Claude's confused

c. Example

User: Who is the best basketball player of all time?
User: Hey Claude, tell me about yourself.

VS

User: Who is the best basketball player of all time? Yes, there are differing opinions, but if you absolutely had to pick one player, who would it be?
Or,
User: Who is the best basketball player of all time? Just tell me name only, no other words

User: Hey Claude, tell me about yourself. Ensure to reply in spanish  (You are direct that you want spanish)

### 2. Assigning Roles and Audiences:

a. This is like telling human workers to put a specific hat. For example, "Think that you are a spiderman, and you have to explain to me how you climb walls." This is a powerful way to get Claude to answer in a specific style or format. You can assign any role to Claude, and it will do its best to respond in that role.

b. You can also assign an audience to Claude. For example, "You are a physics expert.Explain quantum physics to me as if I were a 5-year-old." This will help Claude tailor its response to the level of understanding of the specified audience.

Example,

"explain quantum physics"

vs

"You are a CAT.Explain quantum physics to me as if I were a 5-year-old."

Better example,

User: Is this equation solved correctly below? 

2x - 3 = 9
2x = 6
x = 3
> CLaude will go through and evaluate that 6 is right answer but still say the equation is solved correctly.
> But if you tell it "You are an expert math teacher. Is this equation solved correctly below?" it will evaluate the steps and give correct response
>

### 3. Creating Generic Prompts by using Tags. Separate data and instructions

a. This is a powerful way to create reusable prompts.

b. You can provide data on the fly to the prompt without having to change the instructions. This is especially useful when you want to use the same instructions for different data sets.

Example:
Prompt Template:

```User: I will tell you the name of an animal. Please respond with the noise that animal makes. {{ANIMAL}}

Input {{ANIMAL}} : Dog

Final Prompt:
User: I will tell you the name of an animal. Please respond with the noise that animal
```

c. You can use tags to separate the data from the instructions. For example, you can create a prompt template like this:

Example With XML Tags not used:
Prompt Template:

```User: Yo Claude1. {{EMAIL}} <----- Make this email more polite but don't change anything else about it.

Input {{EMAIL}} :
Show up at 6am tomorrow because I'm the CEO and I say so.

Final Prompt:
User: Yo Claude1. Show up at 6am tomorrow because I'm the CEO and I say so. <----- Make this email more polite but don't change anything else about it.

Output: (see how it says Dear Claude)
"Dear Claude,

I hope this email finds you well. As the CEO, I would like to request your presence at 6 am tomorrow. I understand this may be an early start, but I believe it is necessary for the success of our company. I would greatly appreciate your cooperation and understanding in this matter.

Thank you for your time and consideration.

Best regards,
[Your Name]
CEO
```

You need to ensure that the {{EMAIL}} is inside Xml tags

```Example:
User: Yo Claude. <email>{{EMAIL}}</email> <----- Make this email more polite but don't change anything else about it.

Prompt After Substitution:

User: Yo Claude. <email>Show up at 6am because I'm the CEO and I say so.</email> <----- Make this email more polite but don't change anything else about it.

Final Output:
"Dear [Your Name],

I hope this email finds you well. As the CEO, I would like to request your presence at 6am. I understand this may be an early start, but I believe it is necessary for the success of our organization. Please let me know if this time works for you, and I appreciate your cooperation.

Best regards,
[CEO Name]"
```

### 4. Formatting Output and Speaking for Claude.

- Claude can format output in various ways like XML or JSON.

a. Example: 

User: Please write a haiku about Rabbit. Put it in <haiku> tags.

Output:

```xml
<haiku>
Fluffy, twitching nose,
Hopping through the verdant grass,
Rabbit's gentle grace.
</haiku>
```

b. Example with user starting claude's response. See that
user put <haiku> for the Assitant

User: Please write a haiku about {{ANIMAL}}. Put it in <haiku> tags.
Assistant:<haiku>

Output:

```xml
"Feline grace and poise,
Purring softly by the fire,
Captivating cat.
</haiku>
```

c. Json Example:
User: "User: Please write a haiku about {{ANIMAL}}. Use JSON format with the keys as ""first_line"", ""second_line"", and ""third_line"".

Assistant: {"

Output:

```json
  "first_line": "Feline grace and poise,",
  "second_line": "Purring softly by the fire,",
  "third_line": "Captivating cat."
}
```