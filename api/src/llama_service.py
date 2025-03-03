import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, logging as hf_logging
import config

logging.basicConfig(level=logging.INFO)
hf_logging.set_verbosity_info()  # или set_verbosity_debug() для детального вывода

class DeepSeekService:
    def __init__(self, model_name: str = "meta-llama/Llama-3.1-8B-Instruct"):
        self.device = torch.device("cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            token=config.HF_token
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            token=config.HF_token
        )

        self.model.eval()
        self.model.to(self.device)

    def predict(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                do_sample=True
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
