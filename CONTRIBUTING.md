# Contributing

## General contribution guidelines

### Style
To maintain consistency and reduce potential errors, please follow the style guide below:
- Code should be written in American English, the standard of the software world. For instance, using variable names with `color` instead of `colour`.
- Comments and documentation should be written in common Australian English.

## Issues

Issues are very valuable to this project and help to maintain a high level of standard/consistency.

Please create issues for any bugs, ideas, refactors or questions you might have about the system.

## Pull Requests

### Purpose

You should be clear which problem you're trying to solve with your contribution.

For example:

> Update README.md

Doesn't tell anyone anything about the purpose of the pull request, or what it intends to achieve

> Update table of contents in README.md so users can find tutorials.md and contributing.md

Tells everyone the problem and actions taken to solve it.

### Quality

Pull requests should avoid spelling mistakes and should be well written in English.

Avoid technical jargon unless it's specified in the [glossary](/docs/glossary.md), which might need updating as technical terms and implementations change.

### Design

Does your pull request contribute to the overall design and aim of the project?

The aim of this repository is:

- To develop the RMIT Hive Ground Control software system so that it can fulfill its requirements.
- To be usable and understandable by any new Hive members or people joining the project.
- To foster and maintain a culture of respect, teamwork and honesty as defined in the Hive constitution.

### Contributor covenant

This repository doesn't have a code of conduct just yet, so be nice.

## AI Policy

### Foreword

While AI can be useful for menial tasks or automation, it's important to understand that it can't replace all the hard work.

Specifically, this policy aims to:
- Protect the safety and wellbeing of Hive team members
- Reduce AI-specific risks from being introduced (like inheriting bias from data, lack of explainability or autonomous behaviour)
- Ensure everyone understands and can manage the risks associated with AI systems.

Where risk is involved, human contribution will always take priority over AI systems. Anything which is part of, or connected to, critical control components, launch control or operator systems should never rely on AI systems for logic or functionality.

### Policy scope

This policy applies to:
- All contributors, volunteers and Hive team members involved in the development, adoption, management, or use of AI systems in Hive Ground Control.
- All AI technologies under Hive's control, including those developed in-house, purchased from vendors or embedded within larger software platforms including cloud-based systems.

We define an AI system as any technology that uses data to make inferences and generate outputs such as predictions, recommendations, or decisions with a degree of autonomy.

This includes, but is not limited to:

- machine learning models
- generative AI tools
- predictive analytic systems
- chatbots that generate their own responses.

It excludes:

- standard spreadsheet formulas
- rule-based automations (such as 'if-then' macros)
- traditional business intelligence dashboards.

If you are uncertain about whether an AI technology falls under this policy, consult relevant Hive team and subteam leads or the repository owners.

### Statements

#### 1. Restrictions
Do not use AI for writing documentation. All documentation must be written by humans, for humans to understand. This includes anything in `/docs/`, as well as any markdown files in the root directory.

#### 2. Disclosure
Please disclose all AI usage in pull requests, commit messages and code comments.

#### 3. Understanding
If using AI to generate any code or other functionality, you must have sufficient understanding of how it works and be able to explain it in detail.

#### 4. Accountability
Failure to follow this policy may result in code not being merged or work being reverted.

In rare instances, a person may be removed from the repository and/or Hive team if they repeatedly fail to follow these guidelines, or sufficient risk is introduced from not following them.
