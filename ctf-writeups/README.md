# CTF Writeups

Records of challenges I have **actually solved**. Each writeup follows a fixed structure, keeps the commands and screenshots from the time, and emphasizes "why I thought this way" rather than a blow-by-blow log.

## Contents

| Platform | Challenge | Category | Status | Directory |
|---|---|---|---|---|
| picoCTF (picoGym) | dont-use-client-side | Web | To do | [picoctf/dont-use-client-side/](picoctf/dont-use-client-side/) |
| picoCTF (picoGym) | 13 | Crypto | Done | [writeup](picoctf/13/writeup.md) |
| picoCTF (picoGym) | information | Forensics | Done | [writeup](picoctf/information/writeup.md) |

> This directory only contains real solving records. Before starting a challenge, read [starter-picks.md](starter-picks.md) first and preserve evidence per the list (command history + screenshots). Put each challenge's screenshots in the `screenshots/` subdirectory of its challenge directory (placeholders already created).

## Writing Workflow (for myself)

1. Open the challenge in picoGym and try independently for 30 minutes first;
2. Preserve evidence as you go: terminal command history, screenshots of key steps (the challenge page, your actions, the flag-submission success page);
3. After solving, complete the writeup following the structure in [template.md](template.md);
4. Put screenshots in each challenge directory's `screenshots/` subdirectory and reference them with placeholders in the body.

## Rules

- **Only write challenges I actually solved**: don't copy others' writeups, don't fabricate the solving process;
- **Don't spoil the experience for others**: flags may be written per picoCTF convention (picoGym challenges are public practice), but keep my own reasoning path and focus on "why I thought of doing this";
- Each writeup must end with a **defensive takeaway**: the real-world weakness the challenge exposes and the corresponding defensive measures.
