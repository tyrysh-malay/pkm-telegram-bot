# Project Brief: Personal Knowledge Management Telegram Bot

## Product definition

This project is a Telegram bot that captures chaotic personal knowledge inputs and turns them into structured Markdown artifacts stored in a Git-backed knowledge base.

The bot should support, over time:

* text messages
* voice notes
* images
* links to articles, GitHub, documentation, and videos
* files and PDFs in later versions

## MVP definition

The MVP should process Telegram text messages end-to-end:

1. receive a text message from Telegram;
2. save raw message metadata in PostgreSQL;
3. enqueue a background processing task;
4. create a Markdown note from the message;
5. save the note under `knowledge-base/inbox/`;
6. persist artifact metadata in PostgreSQL;
7. return a success message to the user.

AI processing, voice transcription, image understanding, link extraction, Git commits, and GitHub push are not part of the first vertical slice.

## Main value

The value is not just “LLM summarization”.

The project should demonstrate:

* multi-modal input handling;
* async backend processing;
* reliable task orchestration;
* structured AI outputs;
* deterministic Markdown generation;
* Git-backed knowledge storage;
* clean architecture;
* portfolio-quality engineering decisions.

## Non-goals for MVP

Do not implement in the MVP:

* web UI;
* multi-user SaaS permissions;
* vector search;
* RAG;
* PDF parsing;
* Obsidian plugin;
* complex autonomous agents;
* LangChain/LangGraph;
* Kubernetes deployment;
* advanced GitHub synchronization;
* automatic publishing.

## Target architecture

Use one repository and two runtime processes:

* `app`: FastAPI + aiogram;
* `worker`: Dramatiq worker.

Infrastructure:

* PostgreSQL for operational state;
* Redis for queue/broker and later rate limits;
* local filesystem for Markdown knowledge base;
* Git integration later.

## Knowledge-base philosophy

PostgreSQL stores operational metadata.

Markdown files are the source of truth for human-readable knowledge artifacts.

The Markdown structure should be compatible with Obsidian:

* YAML frontmatter;
* stable file names;
* tags;
* backlinks;
* local asset links;
* readable headings.

## Engineering principle

Build the project as a sequence of vertical slices.

Each milestone should produce something demonstrable.
