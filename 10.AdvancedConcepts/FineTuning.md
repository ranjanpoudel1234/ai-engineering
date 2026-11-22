https://developers.openai.com/api/docs/guides/supervised-fine-tuning?formatting=json

1. Fine tuning is a powerful technique that allows you to customize a pre-trained model on your specific dataset. This can help the model perform better on tasks that are relevant to your use case. In this section, we will go through the steps of fine-tuning a model using the OpenAI API.

2. Build your dataset.
3. Have evals in place
4. Upload training data
5. Create a fine tuning job
6. Evaluate the result
7. You can also use larger model to create data to fine tune smaller model, which is called distillation. This can be useful when you want to deploy a smaller model that is more efficient, but still want to benefit from the knowledge of a larger model.