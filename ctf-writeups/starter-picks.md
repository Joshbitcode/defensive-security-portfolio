# Starter Challenge Picks (picoGym)

picoGym (https://play.picoctf.org/practice) hosts archived picoCTF problems for free. These three cover three different areas and make good first writeups. **Try each one for ~30 minutes on your own before looking at the hint.**

## 1. dont-use-client-side (Web)

- Event: picoCTF 2019 · Web Exploitation
- Find it: search the title in picoGym
- Expected time: 20–40 minutes
- What you learn: validation logic that lives in frontend JavaScript can be read and bypassed by anyone — sensitive logic and secrets must never ship to the client.
- Tools: browser DevTools (F12)
- Evidence to keep: screenshot of the challenge page, screenshot of the DevTools where you found the logic, screenshot of the successful flag submission
- Hint (only if stuck): view the page source; notice the flag may be split into pieces and joined by a condition check.

## 2. 13 (Cryptography)

- Event: picoCTF 2019 · Cryptography
- Find it: search the title in picoGym
- Expected time: 15–30 minutes
- What you learn: recognizing a classical substitution cipher (ROT13) and decoding it; "reversible encoding used as encryption" is a common real-world mistake.
- Tools: terminal (`tr` or a Python one-liner)
- Evidence to keep: screenshot of the ciphertext, your decode command and its output, screenshot of the successful flag submission
- Hint (only if stuck): the challenge name is the cipher.

## 3. information (Forensics)

- Event: picoCTF 2021 · Forensics
- Find it: search the title in picoGym
- Expected time: 15–40 minutes
- What you learn: metadata leakage in files (images included) — strip EXIF and other embedded info before publishing files.
- Tools: `exiftool`, `strings`, `binwalk`, `cat`
- Evidence to keep: the downloaded file, tool output screenshots, screenshot of the successful flag submission
- Hint (only if stuck): check what kind of file it really is first, then read the descriptive metadata it carries.

## How to run the problems

1. Try each one alone for ~30 minutes first, and keep a log of everything you ran — including the failed attempts. Those failed attempts are the most valuable part of the writeup.
2. Use the hint only after you are stuck; do not read other people's writeups for these three.
3. Finish the writeup the same day, while the thinking is still fresh.
