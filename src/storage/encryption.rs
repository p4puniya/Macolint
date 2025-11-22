use anyhow::{Context, Result};
use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce,
};
use base64::{Engine as _, engine::general_purpose};
use pbkdf2::pbkdf2_hmac;
use sha2::Sha256;

pub struct Encryption {
    cipher: Aes256Gcm,
}

impl Encryption {
    pub fn new(master_key: &str) -> Result<Self> {
        // Derive encryption key from master key using PBKDF2
        let mut key_bytes = [0u8; 32];
        pbkdf2_hmac::<Sha256>(
            master_key.as_bytes(),
            b"macolint-salt-v1", // Salt for key derivation
            100000,              // Iterations
            &mut key_bytes,
        );
        
        let key = Key::<Aes256Gcm>::from_slice(&key_bytes);
        let cipher = Aes256Gcm::new(key);
        
        Ok(Self { cipher })
    }

    pub fn encrypt(&self, plaintext: &str) -> Result<String> {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        let ciphertext = self
            .cipher
            .encrypt(&nonce, plaintext.as_bytes())
            .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;
        
        // Combine nonce and ciphertext: nonce (12 bytes) + ciphertext
        let mut combined = nonce.to_vec();
        combined.extend_from_slice(&ciphertext);
        
        Ok(general_purpose::STANDARD.encode(combined))
    }

    pub fn decrypt(&self, ciphertext: &str) -> Result<String> {
        let combined = general_purpose::STANDARD
            .decode(ciphertext)
            .context("Failed to decode base64 ciphertext")?;
        
        if combined.len() < 12 {
            anyhow::bail!("Ciphertext too short");
        }
        
        // Extract nonce (first 12 bytes) and ciphertext (rest)
        let nonce = Nonce::from_slice(&combined[..12]);
        let ciphertext = &combined[12..];
        
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext)
            .map_err(|e| anyhow::anyhow!("Decryption failed: {}", e))?;
        
        String::from_utf8(plaintext).context("Decrypted data is not valid UTF-8")
    }
}

