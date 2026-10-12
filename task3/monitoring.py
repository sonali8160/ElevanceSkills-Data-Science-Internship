# task3/monitoring.py


class Monitor:

    def __init__(self):
        self.metrics = {
            "latency": [],
            "failures": 0,
            "confidence": [],
            "escalations": 0
        }

    def record_latency(self, value):
        self.metrics["latency"].append(value)

    def record_failure(self):
        self.metrics["failures"] += 1

    def record_confidence(self, value):
        self.metrics["confidence"].append(value)

    def record_escalation(self):
        self.metrics["escalations"] += 1

    def summary(self):
        return self.metrics