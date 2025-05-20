import base64

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
#
# embed_model = OpenAIEmbedding(embed_batch_size=10)
# Settings.embed_model = embed_model
def get_b64_image_from_path(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

from openai import OpenAI

client = OpenAI(api_key='YOUR_API_KEY', base_url='https://huice-pqlwftq3uh57.gear-c1.openbayes.net/v1')
model_name = "OpenGVLab/InternVL2_5-4B"
image_b64 = get_b64_image_from_path(r"C:\Users\86134\Desktop\cc.png")

response = client.chat.completions.create(
    model=model_name,
    messages=[{
        'role':
        'user',
        'content': [{
            'type': 'text',
            'text': '请尽可能详细的描述你在图片中看到的所有内容,从多个角度来描述图片上的信息',
        }, {
            'type': 'image_url',
            "image_url":{"url": f"data:image/png;base64,{image_b64}"}
        }],
    }],
    temperature=0.8,
    top_p=0.8)
print(response)