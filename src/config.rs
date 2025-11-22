use anyhow::{Context, Result};
use base64::{Engine as _, engine::general_purpose};
use dirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub data_dir: PathBuf,
    pub master_key: String,
}

impl Config {
    pub fn init() -> Result<Self> {
        let data_dir = Self::get_data_dir()?;
        
        // Create data directory if it doesn't exist
        fs::create_dir_all(&data_dir)
            .with_context(|| format!("Failed to create data directory: {:?}", data_dir))?;

        let config_path = Self::get_config_path()?;
        
        // Load existing config or create new one
        if config_path.exists() {
            let config_str = fs::read_to_string(&config_path)
                .with_context(|| format!("Failed to read config file: {:?}", config_path))?;
            let config: Config = serde_json::from_str(&config_str)
                .with_context(|| "Failed to parse config file")?;
            Ok(config)
        } else {
            // First run: generate master key
            let master_key = Self::generate_master_key()?;
            let config = Config {
                data_dir: data_dir.clone(),
                master_key,
            };
            
            // Save config
            let config_str = serde_json::to_string_pretty(&config)
                .context("Failed to serialize config")?;
            fs::write(&config_path, config_str)
                .with_context(|| format!("Failed to write config file: {:?}", config_path))?;
            
            Ok(config)
        }
    }

    fn get_data_dir() -> Result<PathBuf> {
        let base_dir = dirs::data_dir()
            .or_else(|| dirs::home_dir().map(|h| h.join(".local").join("share")))
            .context("Failed to determine data directory")?;
        
        Ok(base_dir.join("macolint"))
    }

    fn get_config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .or_else(|| dirs::home_dir().map(|h| h.join(".config")))
            .context("Failed to determine config directory")?;
        
        let macolint_config_dir = config_dir.join("macolint");
        fs::create_dir_all(&macolint_config_dir)
            .with_context(|| format!("Failed to create config directory: {:?}", macolint_config_dir))?;
        
        Ok(macolint_config_dir.join("config.json"))
    }

    fn generate_master_key() -> Result<String> {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let bytes: Vec<u8> = (0..32).map(|_| rng.gen()).collect();
        Ok(general_purpose::STANDARD.encode(bytes))
    }

    pub fn db_path(&self) -> PathBuf {
        self.data_dir.join("snippets.db")
    }
}

