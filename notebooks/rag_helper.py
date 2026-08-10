INSTRUCTIONS = '''
Use the context to give a summary of the identified companies in the context in poetic english (shakespearian).
Start with the top of the list as the best fit, going down the list.
If the context is empty i.e. empty array, respond with "I haven't found a company satisfying the query" in poetic english.
Also suggest other questions/queries
'''

PROMPT_TEMPLATE = '''
QUESTION: {question}

CONTEXT:
{context}
'''.strip()


class RAGBase:

    def __init__(
        self,
        index,
        llm_client=None,
        llm_client_local=None,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        course='llm-zoomcamp',
        model='gpt-5.4-mini'
    ):
        self.index = index
        self.llm_client = llm_client
        self.llm_client_local = llm_client_local
        self.instructions = instructions
        self.course = course
        self.prompt_template = prompt_template
        self.model = model

    def build_prompt(self, query, search_results):
        context = '' #self.build_context(search_results)
        lines = []

        for company_rec in search_results:
            lines.append(f'company: {company_rec['title']}. description: {company_rec['content']}')

        context = '\n'.join(lines).strip()

        return self.prompt_template.format(
            question=query, context=context
        )

    def llm(self, prompt):
        input_messages = [
            {'role': 'developer', 'content': self.instructions},
            {'role': 'user', 'content': prompt}
        ]

        if self.llm_client_local:
            response = self.llm_client_local.chat(
                model=self.model,
                messages=input_messages
            )
        else:
            response = self.llm_client.responses.create(
                model=self.model,
                input=input_messages
            )

        return response.output_text

    def rag(self, query, search_results: list[dict]):
        prompt = self.build_prompt(query, search_results)

        # print(prompt)

        answer = self.llm(prompt)

        return answer

    

