"""Demo-only provider plugin. Its answers are FIXTURES, never real LLM judgments."""

class Client:
    def complete(self, spec, system, user):
        return "DEMO FIXTURE: No real AI assessment performed."
