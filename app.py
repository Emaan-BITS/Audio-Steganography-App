import streamlit as st
import tempfile
import os
from Code2 import embed, extract

# ===== Configuration Constants =====
PHASE_ENCODE_FREQ = 5000
CHUNK_SIZE = 1024
HOP_LENGTH = CHUNK_SIZE // 4
LSB_LAYERS = 1
ECC_LENGTH = 16

# ===== Page Setup & Custom CSS (Tech Vibe) =====
st.set_page_config(page_title="Data Obfuscation & Security", page_icon="🛡️", layout="centered")

# Inject Custom CSS for the Cyber/Tech aesthetic
st.markdown("""
<style>
    /* Main Background: Dark Cyberpunk Grid */
    [data-testid="stAppViewContainer"] {
        background-color: #050810;
        background-image: 
            linear-gradient(rgba(0, 255, 204, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 204, 0.05) 1px, transparent 1px);
        background-size: 35px 35px;
        background-position: center center;
    }
    
    /* Transparent Header */
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(10, 15, 25, 0.8);
        border-radius: 8px;
        padding: 5px;
        border: 1px solid rgba(0, 255, 204, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        color: #a0aec0 !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #00ffcc !important;
    }

    /* Inputs & Textareas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(0, 0, 0, 0.6) !important;
        color: #00ffcc !important;
        border: 1px solid rgba(0, 255, 204, 0.3) !important;
        border-radius: 5px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border: 1px solid #00ffcc !important;
        box-shadow: 0 0 5px rgba(0, 255, 204, 0.5) !important;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #00ffcc 0%, #0066ff 100%) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: none !important;
        box-shadow: 0 0 10px rgba(0, 255, 204, 0.4) !important;
        transition: 0.3s ease-in-out !important;
        border-radius: 6px;
        width: 100%;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.8) !important;
        transform: scale(1.02);
    }

    /* Drag & Drop Upload Box */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(10, 20, 30, 0.7) !important;
        border: 2px dashed #00ffcc !important;
        border-radius: 10px;
        transition: all 0.3s;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background-color: rgba(0, 255, 204, 0.1) !important;
        border-color: #ffffff !important;
    }
    
    /* Typography adjustments */
    h1, h2, h3, p, label {
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ===== App Header =====
st.markdown("<h1 style='text-align: center; color: #00ffcc; font-size: 2.2rem;'>Data Obfuscation and Security</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #a0aec0; font-size: 1.1rem; margin-bottom: 2rem;'>Using Multi-Algorithm Encryption and Audio Steganography</h3>", unsafe_allow_html=True)

# Create two tabs for the UI
tab1, tab2 = st.tabs(["🛡️ Encrypt & Conceal Data", "🔍 Decrypt & Extract Data"])

# ----- TAB 1: EMBED -----
with tab1:
    st.markdown("### 🔐 Secure Your Message")
    
    cover_audio = st.file_uploader("📂 Drag & Drop Cover Audio (.wav)", type=["wav"], key="cover")
    secret_text = st.text_area("📝 Enter Secret Payload to Obfuscate")
    password = st.text_input("🔑 Encryption Key (Password)", type="password", key="pass_embed")

    st.write("") # Spacer
    if st.button("INITIALIZE ENCRYPTION & STEGANOGRAPHY"):
        if cover_audio and secret_text and password:
            with st.spinner("Executing AES-ChaCha20 Encryption and Phase Modulation..."):
                
                # Save uploaded audio to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_cover:
                    temp_cover.write(cover_audio.read())
                    temp_cover_path = temp_cover.name
                
                temp_stego_path = "temp_stego_output.wav"

                try:
                    # Call your Code2.py embed function
                    embed(
                        plaintext=secret_text.encode('utf-8'),
                        k1=password.encode('utf-8'),
                        cover_audio_path=temp_cover_path,
                        output_path=temp_stego_path,
                        freq=PHASE_ENCODE_FREQ,
                        chunk_size=CHUNK_SIZE,
                        hop_length=HOP_LENGTH,
                        lsb_layers=LSB_LAYERS,
                        ecc_length=ECC_LENGTH,
                        debug_out=False
                    )
                    
                    st.success("✅ Payload Successfully Encrypted and Embedded!")
                    
                    # Provide a download button for the new audio file
                    with open(temp_stego_path, "rb") as f:
                        st.download_button(
                            label="📥 DOWNLOAD SECURE AUDIO (.wav)",
                            data=f,
                            file_name="secure_stego_audio.wav",
                            mime="audio/wav"
                        )
                except Exception as e:
                    st.error(f"⚠️ System Error: {e}")
                finally:
                    # Clean up temp files
                    if os.path.exists(temp_cover_path): os.remove(temp_cover_path)
        else:
            st.warning("⚠️ Access Denied: Missing Audio, Payload, or Key.")

# ----- TAB 2: EXTRACT -----
with tab2:
    st.markdown("### 🔓 Extract Hidden Payload")
    
    stego_audio = st.file_uploader("📂 Drag & Drop Stego Audio (.wav)", type=["wav"], key="stego")
    password_ext = st.text_input("🔑 Decryption Key (Password)", type="password", key="pass_ext")

    st.write("") # Spacer
    if st.button("RUN EXTRACTION ALGORITHM"):
        if stego_audio and password_ext:
            with st.spinner("Extracting Quantum Phase Data & Decrypting..."):
                
                # Save uploaded stego audio to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_stego:
                    temp_stego.write(stego_audio.read())
                    temp_stego_path = temp_stego.name
                
                try:
                    # Call your Code2.py extract function
                    extracted_bytes = extract(
                        stego_audio_path=temp_stego_path,
                        k1=password_ext.encode('utf-8'),
                        freq=PHASE_ENCODE_FREQ,
                        chunk_size=CHUNK_SIZE,
                        hop_length=HOP_LENGTH,
                        lsb_layers=LSB_LAYERS,
                        ecc_length=ECC_LENGTH,
                        debug_out=False
                    )
                    
                    st.success("✅ Signal Decoded & Signature Verified!")
                    
                    # Display the secret message beautifully
                    st.info(f"**DECRYPTED PAYLOAD:**\n\n{extracted_bytes.decode('utf-8', errors='ignore')}")
                    
                except ValueError:
                    st.error("❌ Decryption Failed! Invalid Key or Corrupted Audio Signature.")
                except Exception as e:
                    st.error(f"⚠️ System Error: {e}")
                finally:
                    # Clean up temp files
                    if os.path.exists(temp_stego_path): os.remove(temp_stego_path)
        else:
            st.warning("⚠️ Access Denied: Please provide the target audio and decryption key.")