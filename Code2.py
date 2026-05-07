#pip install numpy librosa soundfile pycryptodomex reedsolo

import numpy as np
import librosa
import soundfile as sf
from Crypto.Cipher import AES, ChaCha20
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from reedsolo import RSCodec

# ===== Helper Functions =====
def int16_to_float(audio_int16: np.ndarray) -> np.ndarray:
    return audio_int16.astype(np.float32) / 32768.0

def float_to_int16(audio_float: np.ndarray) -> np.ndarray:
    return np.clip(audio_float * 32768.0, -32768, 32767).astype(np.int16)

def derive_key(password: bytes, salt: bytes) -> bytes:
    return PBKDF2(password, salt, dkLen=32, count=1000000) #type: ignore

# ===== Vectorized XOR LSB Coding Functions =====
def xor_lsb_embed(samples: np.ndarray, payload: bytes, lsb_layers: int) -> np.ndarray:
    """Length-prefixed XOR based LSB encoding (Vectorized for speed)."""
    payload_with_length = len(payload).to_bytes(4, byteorder='little') + payload
    payload_bits = np.unpackbits(np.frombuffer(payload_with_length, dtype=np.uint8))
    samples_flat = samples.flatten()

    n_bits = len(payload_bits)
    
    # Pad payload bits with zeros to be a multiple of lsb_layers
    pad_len = (lsb_layers - (n_bits % lsb_layers)) % lsb_layers
    if pad_len > 0:
        payload_bits = np.append(payload_bits, np.zeros(pad_len, dtype=np.uint8))
    
    bits_reshaped = payload_bits.reshape(-1, lsb_layers)
    target_samples = samples_flat[:len(bits_reshaped)]
    
    # Vectorized bit-manipulation
    for bit_pos in range(lsb_layers):
        higher_bit = (target_samples >> (bit_pos + 1)) & 1
        new_bit = bits_reshaped[:, bit_pos] ^ higher_bit
        target_samples = (target_samples & ~(1 << bit_pos)) | (new_bit << bit_pos)
    
    samples_flat[:len(bits_reshaped)] = target_samples
    return samples_flat.reshape(samples.shape)

def xor_lsb_extract(samples: np.ndarray, lsb_layers: int) -> bytes:
    """Length-prefixed XOR based LSB decoding (Vectorized for speed)."""
    samples_flat = samples.flatten()

    def extract_bits(num_bits):
        num_samples = (num_bits + lsb_layers - 1) // lsb_layers
        target_samples = samples_flat[:num_samples]
        extracted = np.zeros((num_samples, lsb_layers), dtype=np.uint8)
        for bit_pos in range(lsb_layers):
            lsb = (target_samples >> bit_pos) & 1
            higher = (target_samples >> (bit_pos + 1)) & 1
            extracted[:, bit_pos] = lsb ^ higher
        return extracted.flatten()[:num_bits]

    # Extract the 32-bit integer representing payload length
    len_bits_arr = extract_bits(32)
    payload_length = int.from_bytes(np.packbits(len_bits_arr).tobytes(), byteorder='little')

    # Extract total necessary bits (length prefix + actual payload)
    total_bits = 32 + payload_length * 8
    all_bits = extract_bits(total_bits)
    
    payload_bits = all_bits[32:]
    return np.packbits(payload_bits).tobytes()

# ===== Phase Coding Functions =====
def get_freq_bin(target_freq: int, sr: int, n_fft: int) -> int:
    return int(target_freq * n_fft / sr)

def phase_embed(audio_int16: np.ndarray, data: bytes, sr: int, freq: int, chunk_size: int, hop_length: int) -> np.ndarray:
    audio_float = int16_to_float(audio_int16)
    target_bin = get_freq_bin(freq, sr, chunk_size)
    data_bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))

    # --- THE "BULLETPROOF" FIX ---
    # We force non-overlapping blocks (hop=chunk) and a rectangular window ('boxcar').
    # This completely disables STFT overlap-add smearing, ensuring perfect data survival!
    stft_matrix = librosa.stft(audio_float, n_fft=chunk_size, hop_length=chunk_size, window='boxcar', center=False)
    phases = np.angle(stft_matrix)
    magnitudes = np.abs(stft_matrix)

    if len(data_bits) > phases.shape[1]:
        raise ValueError("Cover audio is too short to hide the encrypted keys.")

    # --- FIX 1: Boost magnitude to survive 16-bit WAV quantization ---
    # (0.01 is loud enough to survive, but quiet enough to be imperceptible)
    magnitudes[target_bin, :len(data_bits)] = np.maximum(magnitudes[target_bin, :len(data_bits)], 0.01)

    # --- FIX 2: Embed Absolute Phase (Maximal Distance) ---
    # 1 -> +pi/2, 0 -> -pi/2 (180 degrees apart for maximum robustness)
    phases[target_bin, :len(data_bits)] = np.where(data_bits == 1, np.pi/2, -np.pi/2)

    # Reconstruct audio mathematically identically
    modified_stft = magnitudes * np.exp(1j * phases)
    modified_audio = librosa.istft(modified_stft, n_fft=chunk_size, hop_length=chunk_size, window='boxcar', center=False, length=len(audio_float))

    return float_to_int16(modified_audio)

def phase_extract(audio_int16: np.ndarray, sr: int, data_length: int, freq: int, chunk_size: int, hop_length: int) -> bytes:
    audio_float = int16_to_float(audio_int16)
    target_bin = get_freq_bin(freq, sr, chunk_size)
    num_bits = data_length * 8

    # Extract using the exact same non-overlapping boxcar parameters
    stft_matrix = librosa.stft(audio_float, n_fft=chunk_size, hop_length=chunk_size, window='boxcar', center=False)
    phases = np.angle(stft_matrix)

    extracted_phases = phases[target_bin, :num_bits]

    # --- FIX 3: Angular Distance Decoder ---
    # Measure angular distance to pi/2 (Binary 1) and -pi/2 (Binary 0)
    dist_to_pi2 = np.abs(extracted_phases - np.pi/2)
    dist_to_npi2 = np.abs(extracted_phases - (-np.pi/2))

    # Handle circular angular wrap-around (e.g., -0.9pi and 0.9pi are close together)
    dist_to_pi2 = np.minimum(dist_to_pi2, 2*np.pi - dist_to_pi2)
    dist_to_npi2 = np.minimum(dist_to_npi2, 2*np.pi - dist_to_npi2)

    # Pick whichever phase target it is closest to
    data_bits = np.where(dist_to_pi2 < dist_to_npi2, 1, 0).astype(np.uint8)

    return np.packbits(data_bits).tobytes()[:data_length]

# ===== Main Cryptography & Stego Functions =====
def embed(plaintext: bytes, k1: bytes, cover_audio_path: str, output_path: str, freq: int, chunk_size: int, hop_length: int, lsb_layers: int, ecc_length: int, debug_out: bool=True):
    audio_int16, sr = sf.read(cover_audio_path, dtype='int16')

    # Crypto Initialization
    salt = get_random_bytes(16)
    k1_prime = derive_key(k1, salt)
    k2 = get_random_bytes(32)

    # Encrypt payload (Using robust PKCS7 padding)
    cipher_aes = AES.new(k1_prime, AES.MODE_CBC, iv=salt[:16])
    ct1 = cipher_aes.encrypt(pad(plaintext, AES.block_size))

    cipher_chacha = ChaCha20.new(key=k2, nonce=salt[:12])
    ct2 = cipher_chacha.encrypt(ct1)

    # Encrypt k2
    cipher_k2 = AES.new(k1_prime, AES.MODE_CBC, iv=salt[:16])
    encrypted_k2 = cipher_k2.encrypt(pad(k2, AES.block_size)) # Will strictly be 48 bytes

    # Add error correction
    rs = RSCodec(ecc_length)
    ct2_encoded = bytes(rs.encode(ct2))
    encrypted_k2_encoded = bytes(rs.encode(encrypted_k2)) # 48 + ECC_LENGTH bytes

    # Phase coding embedding (Keys)
    audio_int16 = phase_embed(audio_int16, encrypted_k2_encoded + salt, sr, freq, chunk_size, hop_length)

    # LSB embedding (Payload)
    audio_int16 = xor_lsb_embed(audio_int16, ct2_encoded, lsb_layers)

    if debug_out:
        print("Embed:")
        print(f"  encrypted_k2_encoded:", encrypted_k2_encoded.hex(":", -2))
        print(f"  ct2_encoded         :", ct2_encoded.hex(":", -2), "\n")

    sf.write(output_path, audio_int16, sr, subtype='PCM_16')

def extract(stego_audio_path: str, k1: bytes, freq: int, chunk_size: int, hop_length: int, lsb_layers: int, ecc_length: int, debug_out: bool=True):
    audio_int16, sr = sf.read(stego_audio_path, dtype='int16')

    # 1. Phase extraction: get encrypted_k2_encoded + salt
    phase_data_length = (48 + ecc_length) + 16 
    phase_bytes = phase_extract(audio_int16, sr, phase_data_length, freq, chunk_size, hop_length)
    encrypted_k2_encoded = phase_bytes[:48+ecc_length]
    salt = phase_bytes[48+ecc_length:]

    # 2. RS Decode Key
    rs = RSCodec(ecc_length)
    try:
        encrypted_k2 = bytes(rs.decode(encrypted_k2_encoded)[0])[:48]
    except Exception as e:
        raise ValueError("Error correcting encrypted_k2 failed: " + str(e))

    # 3. Derive keys and decrypt K2
    k1_prime = derive_key(k1, salt)
    cipher_k2 = AES.new(k1_prime, AES.MODE_CBC, iv=salt[:16])
    k2 = unpad(cipher_k2.decrypt(encrypted_k2), AES.block_size)

    # 4. LSB extraction & RS Decode Payload
    ct2_encoded = xor_lsb_extract(audio_int16, lsb_layers)
    try:
        ct2 = bytes(rs.decode(ct2_encoded)[0])
    except Exception as e:
        raise ValueError("Error correcting ct2 failed: " + str(e))

    # 5. Decrypt Payload
    cipher_chacha = ChaCha20.new(key=k2, nonce=salt[:12])
    ct1 = cipher_chacha.decrypt(ct2)

    cipher_aes = AES.new(k1_prime, AES.MODE_CBC, iv=salt[:16])
    plaintext = unpad(cipher_aes.decrypt(ct1), AES.block_size)

    if debug_out:
        print("Extract:")
        print(f"  encrypted_k2_encoded:", encrypted_k2_encoded.hex(":", -2))
        print(f"  ct2_encoded         :", ct2_encoded.hex(":", -2), "\n")

    return plaintext