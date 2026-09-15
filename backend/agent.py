"""
Agentic RAG Module
Intelligent agent that evaluates user input, decides whether to execute document retrieval,
handles multi-turn conversation context, and synthesizes grounded answers with source citations.
"""

import json
import re
import os
from typing import List, Dict, Any, Tuple, Optional
from backend.config import OPENAI_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, OPENAI_MODEL, GEMINI_MODEL
from backend.rag_tool import search_pdf_knowledge_base
from backend.vector_store import list_indexed_documents


class AgenticRAGBot:
    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def clear_history(self):
        self.history = []

    def process_query(
        self, 
        user_query: str, 
        session_history: List[Dict[str, str]] = None,
        attached_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user query.
        1. Accepts optional session_history list for session context.
        2. Accepts optional attached_filename to focus analysis on a target PDF.
        3. Decides if vector retrieval is needed.
        4. Executes retrieval if necessary.
        5. Formulates grounded response.
        """
        if session_history is not None:
            self.history = session_history

        # Step 1: Check if documents are uploaded
        indexed_docs = list_indexed_documents()
        has_documents = len(indexed_docs) > 0

        # Step 2: Agent Decision - Does this query need document search?
        needs_search, search_query = self._evaluate_search_need(user_query, has_documents)

        sources = []
        retrieved_context = ""
        tool_used = False

        # Step 3: Tool Execution (if search is needed or file is attached)
        if (needs_search or attached_filename) and has_documents:
            tool_used = True
            tool_result = search_pdf_knowledge_base(
                query=search_query or user_query, 
                top_k=8,
                target_filename=attached_filename
            )
            retrieved_context = tool_result["context"]
            sources = tool_result["sources"]

        # Step 4: Synthesize Answer
        answer = self._generate_answer(
            user_query=user_query,
            needs_search=needs_search or bool(attached_filename),
            has_documents=has_documents,
            retrieved_context=retrieved_context,
            sources=sources
        )

        # Deduplicate sources while preserving order
        unique_sources = []
        seen = set()
        for src in sources:
            key = (src["filename"], src["page_number"])
            if key not in seen:
                seen.add(key)
                unique_sources.append(src)

        # Step 5: Record in conversation history
        self.history.append({"role": "user", "content": user_query})
        self.history.append({"role": "assistant", "content": answer})

        return {
            "answer": answer,
            "searched_docs": tool_used,
            "search_query": search_query if tool_used else None,
            "sources": unique_sources,
            "has_documents": has_documents,
            "attached_filename": attached_filename
        }


    def _evaluate_search_need(self, user_query: str, has_documents: bool) -> Tuple[bool, Optional[str]]:
        """
        Agent router: Evaluates whether document search is needed, and if so,
        reformulates a standalone search query taking history into account.
        """
        if not has_documents:
            return False, None

        # Build prompt for decision maker
        recent_history = self._format_recent_history(max_turns=3)
        
        system_prompt = (
            "You are an intelligent document routing agent for a company knowledge base.\n"
            "Your task is to analyze the latest user message (and conversation history) and decide whether "
            "it requires searching internal company documents/PDFs to answer.\n\n"
            "Rules:\n"
            "1. Set 'needs_search': true if the question asks about company policies, procedures, rules, "
            "leave, benefits, technical docs, guidelines, or specific information likely stored in uploaded PDFs.\n"
            "2. Set 'needs_search': false for general knowledge, math calculations (e.g. 25x4), greetings, "
            "chitchat, or requests unrelated to documents.\n"
            "3. If 'needs_search' is true, provide an optimized 'search_query' string that resolves coreferences "
            "(e.g. if previous message was 'What is leave policy?' and current is 'How many days does it allow?', "
            "the search query should be 'Leave policy allowed days').\n\n"
            "Respond ONLY with a valid JSON object in this format:\n"
            '{"needs_search": true|false, "search_query": "string or null"}'
        )

        prompt = f"Conversation History:\n{recent_history}\n\nLatest User Message: \"{user_query}\"\nJSON Decision:"

        try:
            raw_response = self._call_llm(system_prompt=system_prompt, user_prompt=prompt, temperature=0.0)
            
            # Clean JSON response
            cleaned_json = raw_response.strip()
            if cleaned_json.startswith("```"):
                cleaned_json = cleaned_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            parsed = json.loads(cleaned_json)
            needs_search = bool(parsed.get("needs_search", True))
            search_query = parsed.get("search_query") or user_query
            return needs_search, search_query
        except Exception as e:
            # Fallback heuristic if LLM call fails or key is missing
            return self._heuristic_search_decision(user_query)

    def _heuristic_search_decision(self, user_query: str) -> Tuple[bool, Optional[str]]:
        """
        Fallback decision heuristic when LLM is unavailable or API key is not set.
        """
        q_lower = user_query.strip().lower()
        import re

        # Greetings & pleasantries (use word boundary so names like Aashi don't trigger "hi")
        is_greeting = bool(re.search(r"\b(hello|hi|hey|greetings|thanks|thank\s+you)\b", q_lower))
        if is_greeting and len(q_lower.split()) <= 3:
            return False, None

        # Math and arithmetic queries (e.g. "What is 25 x 4?", "calculate 100/5", "25*4")
        math_words = ["plus", "minus", "times", "divided by", "multiply", "calculate", "compute", "sqrt", "percentage", "sum of"]
        is_math_expr = bool(re.match(r"^\s*(what\s+is\s+|calculate\s+|compute\s+)?[\d\s\+\-\*\/\(\)\.xX\=]+\??\s*$", q_lower))
        has_math_words = any(w in q_lower for w in math_words)
        
        if is_math_expr or has_math_words:
            return False, None

        # Resolve simple follow-up pronouns with previous document query if available
        search_query = user_query
        if any(pronoun in q_lower for pronoun in ["it", "its", "this", "that", "they", "them", "these"]):
            for msg in reversed(self.history):
                if msg["role"] == "user":
                    prev_text = msg["content"].lower()
                    if not any(w in prev_text for w in math_words) and not re.match(r"^\s*(what\s+is\s+|calculate\s+|compute\s+)?[\d\s\+\-\*\/\(\)\.xX\=]+\??\s*$", prev_text):
                        search_query = f"{msg['content']} {user_query}"
                        break

        return True, search_query

    def _generate_answer(
        self,
        user_query: str,
        needs_search: bool,
        has_documents: bool,
        retrieved_context: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        Generates final answer using retrieved context or general knowledge.
        Strictly enforces non-hallucination when searching documents.
        """
        recent_history = self._format_recent_history(max_turns=4)

        if needs_search:
            if not retrieved_context or "No relevant document passages found" in retrieved_context:
                return "I searched the uploaded documents, but could not find any information relevant to your question."

            system_prompt = (
                "You are an accurate, professional Company Knowledge Assistant.\n"
                "Answer the user's question STRICTLY based on the provided retrieved document passages below.\n\n"
                "STRICT GROUNDING RULES:\n"
                "1. Base your answer ONLY on facts present in the retrieved passages.\n"
                "2. Carefully inspect all retrieved passages (including presentation slides, diagrams, and multi-page PDF documents).\n"
                "3. If the passages contain the answer, provide a clear, thorough answer detailing all requested facts (e.g. problem statement IDs, titles, stakeholders, or policies).\n"
                "4. If the passages genuinely do not contain enough information to answer the question, state: "
                "'The provided documents do not contain enough information to answer this question.'\n"
                "5. Do NOT make up, assume, or extrapolate information not supported by the passages.\n"
                "6. Do NOT manually invent citation text like '(Source: ...)'; the system UI automatically displays source metadata cards below your answer."
            )


            prompt = (
                f"Conversation History:\n{recent_history}\n\n"
                f"Retrieved Document Passages:\n{retrieved_context}\n\n"
                f"User Question: {user_query}\n\n"
                "Grounded Answer:"
            )

        else:
            system_prompt = (
                "You are a helpful, professional internal company assistant.\n"
                "Answer the user's request directly and concisely."
            )
            if not has_documents:
                system_prompt += " Note: No documents are currently uploaded to the knowledge base."

            prompt = f"Conversation History:\n{recent_history}\n\nUser Question: {user_query}\n\nAnswer:"

        try:
            return self._call_llm(system_prompt=system_prompt, user_prompt=prompt, temperature=0.2)
        except Exception as e:
            import os
            import time
            from dotenv import load_dotenv
            load_dotenv(override=True)
            has_keys = bool(os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip())
            
            err_msg = str(e)
            
            if not has_keys:
                if not needs_search:
                    match = re.search(r"(\d+)\s*([\+\-\*xX\/])\s*(\d+)", user_query)
                    if match:
                        n1, op, n2 = int(match.group(1)), match.group(2).lower(), int(match.group(3))
                        res = n1 * n2 if op in ['*', 'x'] else (n1 + n2 if op == '+' else (n1 - n2 if op == '-' else n1 / n2))
                        return f"The calculation result is **{res}**."
                    return "Hello! I am your Company Knowledge Assistant. How can I help you today?"
                
                return (
                    "ℹ️ **Note: Add your GEMINI_API_KEY or OPENAI_API_KEY to `.env` to enable full AI answers.**\n\n"
                    "Below are the relevant text passages retrieved from your uploaded document:\n\n"
                    f"{retrieved_context}"
                )

            # Fallback if API rate limit (429 / RESOURCE_EXHAUSTED) occurs
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
                if not needs_search:
                    match = re.search(r"(\d+)\s*([\+\-\*xX\/])\s*(\d+)", user_query)
                    if match:
                        n1, op, n2 = int(match.group(1)), match.group(2).lower(), int(match.group(3))
                        res = n1 * n2 if op in ['*', 'x'] else (n1 + n2 if op == '+' else (n1 - n2 if op == '-' else n1 / n2))
                        return f"{n1} {op} {n2} = **{res}**"
                if retrieved_context:
                    return (
                        "⚠️ **API Rate Limit Exceeded (Free Tier Quota)**: Displaying retrieved document context directly:\n\n"
                        f"{retrieved_context}"
                    )

            return f"An error occurred while generating the answer: {err_msg}"

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """
        Unified LLM client caller supporting Gemini and OpenAI with auto-retry for rate limits.
        """
        import time
        from dotenv import load_dotenv
        load_dotenv(override=True)

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

        provider = LLM_PROVIDER

        if provider == "auto":
            if gemini_key:
                provider = "gemini"
            elif openai_key:
                provider = "openai"
            else:
                raise ValueError("No API key set for OpenAI or Gemini.")

        if provider == "gemini":
            from google import genai
            client = genai.Client(api_key=gemini_key)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            model_candidates = [
                os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
                "gemini-flash-latest",
                "gemini-3.6-flash",
                "gemini-2.5-flash",
                "gemini-flash-lite-latest"
            ]
            last_err = None
            
            for model_name in dict.fromkeys(model_candidates):
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=full_prompt,
                        )
                        return response.text.strip()
                    except Exception as err:
                        last_err = err
                        err_str = str(err)
                        if ("RESOURCE_EXHAUSTED" in err_str or "429" in err_str) and attempt == 0:
                            time.sleep(2)
                            continue
                        break
            
            # If Gemini fails and OpenAI key exists, seamlessly call OpenAI
            if openai_key:
                try:
                    from openai import OpenAI
                    o_client = OpenAI(api_key=openai_key)
                    res = o_client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=temperature
                    )
                    return res.choices[0].message.content.strip()
                except Exception as o_err:
                    print(f"OpenAI fallback error: {o_err}")

            if last_err:
                raise last_err

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _format_recent_history(self, max_turns: int = 4) -> str:
        if not self.history:
            return "None"
        
        recent = self.history[-max_turns*2:]
        formatted = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)
