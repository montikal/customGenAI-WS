from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

class FlanLLM:
    def __init__(self, model_name="google/flan-t5-base", device=None):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def generate(self, prompt: str, max_new_tokens=180) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True).to(self.device)
        out = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=4,
            do_sample=False,
            early_stopping=True,
        )
        return self.tokenizer.decode(out[0], skip_special_tokens=True).strip()
