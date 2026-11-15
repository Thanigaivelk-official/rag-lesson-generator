"""
generator.py — AI content generator module.

Responsible for producing educational lessons via the LLM.
Supports both real OpenAI calls and a mock mode for testing.
"""

import logging
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import config
from schemas import GeneratedLesson, GenerationRequest, LearnerLevel
from prompts import GENERATOR_SYSTEM_PROMPT, build_generator_user_prompt

logger = logging.getLogger(__name__)


# ======================================================================= #
#  Mock lesson (used when MOCK_MODE=true or no API key is set)
# ======================================================================= #

MOCK_LESSON = """# Introduction to RAG (Retrieval-Augmented Generation)

## Learning Objectives
- Understand what RAG is and why it was created.
- Learn how RAG combines information retrieval with language generation.
- Understand the step-by-step RAG pipeline.
- Compare RAG with traditional LLM-only systems.
- Identify benefits and limitations of RAG.

## Introduction to AI
Artificial Intelligence, or AI, is the ability of a computer program to perform tasks that normally require human thinking. Think of AI as a very smart assistant that can read, write, understand language, and answer questions.

One type of AI that has become very popular is called a **Large Language Model**, or **LLM**. An LLM is a computer program trained on billions of pages of text from the internet, books, and articles. After this training, it can generate human-like text, answer questions, and have conversations.

**Example:** ChatGPT, made by OpenAI, is an LLM. When you ask it a question, it uses the patterns it learned during training to give you an answer.

However, LLMs have an important limitation — they only know what was in their training data. They cannot access new information after training is complete.

## What is RAG?
**RAG** stands for **Retrieval-Augmented Generation**. Let us break this down word by word:

- **Retrieval** = Finding and fetching relevant information from a collection of documents.
- **Augmented** = Enhanced or improved — adding something extra to make it better.
- **Generation** = Creating text as an answer.

So RAG means: **Find relevant information first, then use it to generate a better answer.**

RAG is a method that helps AI systems answer questions more accurately by first searching through real documents and then using that information to write an answer.

## Why Do We Need RAG?

### Problems with Traditional LLM-Only Answers
When you ask an LLM a question, it answers based only on what it learned during training. This creates several problems:

1. **Outdated information:** LLMs are trained once and do not automatically update. If you ask about something that happened after training, the LLM may not know.
2. **Hallucination:** Sometimes LLMs confidently give wrong answers because they "guess" based on patterns rather than facts.
3. **No access to private documents:** LLMs cannot read your company's internal reports, your college's syllabus, or a hospital's patient records.
4. **No source citations:** Standard LLMs cannot tell you where their answer came from.

RAG solves all these problems by giving the LLM access to real, up-to-date documents at the time of answering.

**Important clarification:** RAG does NOT retrain or modify the LLM. When you add new documents to a RAG system, the LLM itself is not changed. Instead, those documents are stored in a special database, and when a question is asked, the system retrieves the relevant document chunks and passes them to the LLM in the prompt. The LLM uses this retrieved information to generate its answer.

## How RAG Works — Step by Step

Here is a simple analogy:

**Imagine you are a student writing an exam with an open-book policy.**
- You have your textbooks (the document collection).
- When you get a question, you search your books for relevant pages.
- You read those pages, understand the key points, and write your answer in your own words.

RAG works exactly the same way:
1. Documents are stored in a searchable database.
2. When a question arrives, the system searches for relevant document sections.
3. Those sections are given to the LLM.
4. The LLM writes its answer using that information.

## RAG Architecture Explained

### Step 1: Document Loading
The first step is to collect your documents and load them into the system. These can be PDF files, Word documents, web pages, or any text source.

**Example:** A hospital loads all its medical guidelines and patient care protocols into the RAG system.

### Step 2: Text Chunking
Large documents are too long to process at once, so they are divided into smaller pieces called **chunks**. A chunk is typically a paragraph or a few sentences — a manageable piece of text.

**Example:** A 50-page hospital manual is divided into 200 chunks of about 3–4 sentences each.

### Step 3: Embeddings
Each chunk is converted into a list of numbers called an **embedding** (also called a vector). These numbers capture the *meaning* of the text, not just the words.

**What is an embedding?** Think of it as a unique address for every piece of text. Two chunks that have similar meaning will have similar addresses (numbers that are close to each other), even if the exact words are different.

**Example:** "How to treat a fever" and "Fever treatment guidelines" have different words but similar embeddings because they mean the same thing.

### Step 4: Vector Databases
Embeddings are stored in a special database called a **vector database**. Unlike regular databases that search by exact keywords, a vector database can search by *meaning* — it finds the chunks most similar in meaning to the question.

**Popular vector databases:** Pinecone, ChromaDB, FAISS, Weaviate.

### Step 5: Retrieval
When a user asks a question, that question is also converted to an embedding. The vector database then finds the top K chunks (usually 3–5) whose embeddings are most similar to the question embedding. These chunks are retrieved.

**Example:** A doctor asks: "What is the recommended dosage for paracetamol?" The vector database finds the 3 chunks in the medical manual that are most relevant to this question.

### Step 6: Augmented Prompt
The retrieved chunks are added to the LLM's prompt. The prompt now contains both the user's question AND the relevant document information. This is called the **augmented prompt**.

**Example of an augmented prompt:**
```
Context: [retrieved document chunks about paracetamol dosage]
Question: What is the recommended dosage for paracetamol?
Please answer based on the context provided.
```

### Step 7: Generation
The LLM reads the augmented prompt (which includes the retrieved context) and generates an answer. Because the LLM has actual document information in its prompt, the answer is more accurate and can cite the source.

## Practical Real-World Examples

### Example 1: University Library Chatbot
A university builds a chatbot using RAG.
- **Documents:** All course syllabuses, exam schedules, library rules, and fee structures.
- **User question:** "When is the last date to pay the semester fee?"
- **RAG process:** The system searches the loaded documents, finds the relevant fee schedule chunk, and the LLM generates an accurate answer with the exact date.
- **Without RAG:** The LLM would either not know (data not in training) or guess incorrectly.

### Example 2: Customer Support for an E-commerce Company
An online shopping company uses RAG for customer support.
- **Documents:** Product manuals, return policies, shipping guidelines.
- **User question:** "How do I return a defective product?"
- **RAG process:** The system retrieves the return policy document chunk and generates a step-by-step answer.
- **Without RAG:** The LLM might give generic advice that does not match the company's actual policy.

### Example 3: Legal Document Assistant
A law firm uses RAG to help lawyers search through thousands of case files.
- **Documents:** Past court cases, legal precedents, contracts.
- **User question:** "Find cases where tenant rights were upheld in rental disputes."
- **RAG process:** The vector database retrieves relevant case summaries, and the LLM summarises the key findings.

## RAG vs. Traditional LLM

| Feature | Traditional LLM | RAG System |
|---|---|---|
| Knowledge source | Training data only | Training data + external documents |
| Up-to-date info | No (frozen at training) | Yes (documents can be updated) |
| Access to private docs | No | Yes |
| Hallucination risk | Higher | Lower (grounded in documents) |
| Source citations | No | Yes (can cite document chunks) |
| Retraining needed for new info | Yes | No (just add new documents) |

**Key point:** RAG does NOT require retraining the LLM when new documents are added. You simply add the documents to the vector database.

## Advantages of RAG
1. **Accurate answers:** Grounded in real documents, not guesses.
2. **Up-to-date:** New documents can be added without retraining.
3. **Source transparency:** The system can tell you which document chunk it used.
4. **Private data access:** Can work with internal, private documents.
5. **Cost-effective:** No need to retrain the expensive LLM for every new document.
6. **Domain-specific:** Can be specialised for medicine, law, education, etc.

## Limitations of RAG
1. **Quality depends on documents:** If the documents are outdated or poorly written, answers will be poor.
2. **Retrieval errors:** Sometimes the wrong chunks are retrieved, leading to irrelevant answers.
3. **Chunk boundary issues:** Important information might be split across two chunks and missed.
4. **Context window limits:** LLMs can only read a limited amount of text at once; too many retrieved chunks cause problems.
5. **Not truly "understanding":** The LLM still only generates text — it does not truly reason from first principles.
6. **RAG does not guarantee 100% accuracy:** It significantly reduces hallucinations but does not eliminate them.

## Common Beginner Mistakes
1. **Thinking RAG retrains the LLM:** It does NOT. RAG retrieves information at the time of the question (inference time).
2. **Confusing RAG with fine-tuning:** Fine-tuning actually updates the LLM's weights. RAG does not change the model at all.
3. **Ignoring chunk size:** Too large → irrelevant context. Too small → missing context. Chunk size needs careful tuning.
4. **Skipping the glossary check:** Always test whether a beginner can understand your documentation.
5. **Assuming RAG works without good documents:** Garbage in, garbage out — RAG is only as good as the documents you provide.

## Key Takeaways
- RAG = Retrieval + Augmented + Generation.
- RAG helps LLMs answer questions using real external documents.
- RAG does NOT retrain the LLM — it retrieves documents at inference time.
- The pipeline: Load documents → Chunk → Embed → Store in vector DB → Retrieve → Augment prompt → Generate answer.
- RAG is better than traditional LLMs for domain-specific, up-to-date, and private document queries.
- RAG reduces hallucinations but does not guarantee perfect accuracy.

## Glossary
| Term | Simple Explanation |
|---|---|
| **RAG** | Retrieval-Augmented Generation — an AI method that finds relevant documents before generating an answer. |
| **LLM** | Large Language Model — a powerful AI trained on billions of text examples (e.g., GPT-4, Gemini). |
| **Embedding** | A list of numbers that represents the meaning of a piece of text. Similar texts have similar numbers. |
| **Chunk** | A small piece of a larger document, typically a paragraph or a few sentences. |
| **Vector Database** | A special database that stores embeddings and can search for similar meanings, not just exact words. |
| **Retrieval** | The process of searching the vector database to find the most relevant chunks for a question. |
| **Augmented Prompt** | The question PLUS the retrieved document chunks, all sent together to the LLM. |
| **Inference** | The moment when the AI generates an answer in response to a question (as opposed to training). |

## Knowledge Assessment — 5 Multiple Choice Questions

**Question 1:** What does RAG stand for?
- A) Random Access Generation
- B) Retrieval-Augmented Generation ✓
- C) Recurrent AI Generation
- D) Real-time Answer Generator

✓ **Correct: B.** RAG stands for Retrieval-Augmented Generation — a method that retrieves documents and uses them to generate better answers.

---

**Question 2:** Which of the following correctly describes how RAG handles new documents?
- A) It retrains the LLM every time a new document is added.
- B) It fine-tunes the LLM on the new document.
- C) It stores the new document in the vector database, making it available for retrieval without retraining the LLM. ✓
- D) It ignores new documents; only training data is used.

✓ **Correct: C.** RAG stores new documents in the vector database. The LLM is NOT retrained — documents are retrieved at inference time.

---

**Question 3:** What is an "embedding" in the context of RAG?
- A) A type of document file format.
- B) A numerical representation (list of numbers) that captures the meaning of a piece of text. ✓
- C) The final answer generated by the LLM.
- D) A method of compressing large documents.

✓ **Correct: B.** An embedding is a list of numbers that represents the semantic meaning of text, allowing similar meanings to be found even with different words.

---

**Question 4:** Why is a vector database used in RAG instead of a regular database?
- A) Because vector databases are cheaper.
- B) Because vector databases can store images.
- C) Because vector databases search by semantic similarity (meaning), not just exact keywords. ✓
- D) Because regular databases cannot store text.

✓ **Correct: C.** Vector databases search using meaning (semantic similarity), so they can find relevant chunks even when the question uses different words than the document.

---

**Question 5:** Which of the following is a limitation of RAG?
- A) RAG cannot use external documents.
- B) RAG requires retraining the LLM for every query.
- C) RAG always gives 100% accurate answers.
- D) RAG's answer quality depends on the quality of the documents provided. ✓

✓ **Correct: D.** If the documents are outdated, incomplete, or poorly written, RAG's answers will also be poor. RAG does not guarantee perfect accuracy.
"""


# ======================================================================= #
#  LLM client factory
# ======================================================================= #

def _get_llm():
    """Return a configured ChatOpenAI instance (works with OpenAI, Groq, etc.)."""
    kwargs = {
        "model": config.GENERATOR_MODEL,
        "temperature": config.GENERATOR_TEMPERATURE,
        "api_key": config.get_active_api_key(),
    }
    base_url = config.get_active_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


# ======================================================================= #
#  Public generation function
# ======================================================================= #

def generate_lesson(request: GenerationRequest) -> GeneratedLesson:
    """
    Generate an educational lesson for the given request.

    In mock mode (no API key or MOCK_MODE=true), returns a pre-written
    lesson so the full workflow can be tested without API credits.

    Parameters
    ----------
    request : GenerationRequest
        Topic, learner level, previous feedback, and attempt number.

    Returns
    -------
    GeneratedLesson
        Structured lesson with metadata.
    """
    logger.info(
        "Generator: attempt %d for topic '%s'", request.attempt_number, request.topic
    )

    if config.effective_mock_mode():
        logger.info("Generator: running in MOCK mode.")
        content = MOCK_LESSON
        # Apply previous feedback hint to mock content for testing purposes
        if request.previous_feedback:
            content = content  # mock always passes; real retry tested via stress test
        return GeneratedLesson(
            title="Introduction to RAG (Retrieval-Augmented Generation)",
            content=content,
            topic=request.topic,
            learner_level=request.learner_level,
            attempt_number=request.attempt_number,
        )

    # ---- Real LLM call with Rate Limit retry handling ----
    import time
    llm = _get_llm()
    user_prompt = build_generator_user_prompt(
        topic=request.topic,
        learner_level=request.learner_level.value,
        attempt_number=request.attempt_number,
        previous_feedback=request.previous_feedback,
        improvement_hints=request.improvement_hints,
    )

    messages = [
        SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    logger.debug("Generator: calling LLM with model '%s'", config.GENERATOR_MODEL)

    # Retry up to 3 times on 429 rate limit
    for attempt_retry in range(3):
        try:
            response = llm.invoke(messages)
            break
        except Exception as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str:
                sleep_secs = 12 if "openai/gpt-oss-120b" in config.GENERATOR_MODEL else 5
                logger.warning("Rate limit hit in generator, sleeping %d seconds...", sleep_secs)
                time.sleep(sleep_secs)
            else:
                raise err
    else:
        # Final attempt
        response = llm.invoke(messages)

    content: str = response.content.strip()  # type: ignore[union-attr]

    # Extract title from first heading if present
    title = request.topic
    for line in content.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return GeneratedLesson(
        title=title,
        content=content,
        topic=request.topic,
        learner_level=request.learner_level,
        attempt_number=request.attempt_number,
    )
