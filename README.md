# Data Obfuscation and Security: Audio Steganography

A robust, full-stack Python web application designed for high-security data obfuscation. By combining multi-algorithm cryptographic protocols with advanced audio signal processing, this tool allows users to seamlessly hide and extract confidential text payloads within standard audio files (.wav).

---

## Features

* Multi-Layer Cryptography: Secures your payload using a combination of AES-256 (CBC Mode) and ChaCha20 encryption.
* Audio Steganography: Employs advanced audio manipulation techniques:
  * Phase Coding: Modifies the phase of the audio signal (using non-overlapping STFT) to securely embed cryptographic keys.
  * Vectorized LSB Coding: Uses a high-speed XOR-based Least Significant Bit (LSB) embedding algorithm to hide the encrypted payload directly within the audio samples.
* Error Correction: Integrates Reed-Solomon (RS) Error Correction to ensure the survival and precise extraction of embedded data, even if the audio undergoes minor signal degradation.
* Modern UI: Features a custom, dark-themed web interface built with Streamlit for an intuitive user experience.

---

## Technology Stack

* Frontend: Streamlit
* Cryptography: pycryptodome (AES, ChaCha20, PBKDF2)
* Audio Processing: librosa, soundfile
* Data Manipulation and Math: numpy
* Error Correction: reedsolo

---

## Live Demo

How to Use
Encrypt and Conceal Data
Navigate to the Encrypt and Conceal Data tab.

Upload a standard cover audio file (.wav format).

Enter the secret text payload you wish to hide.

Provide a strong Encryption Key (Password).

Click Initialize and download your newly generated secure stego-audio file.

Decrypt and Extract Data
Navigate to the Decrypt and Extract Data tab.

Upload the stego-audio file containing the hidden data.

Enter the exact Decryption Key (Password) used during encryption.

Click Run Extraction to decode the phase data, verify the signature, and reveal the hidden message.
