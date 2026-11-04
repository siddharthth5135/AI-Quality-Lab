# Fan Not Connecting

If the fan does not appear during BLE discovery, move within 2 meters, disable other Bluetooth accessories, and restart the phone Bluetooth radio.
Confirm the fan is in pairing mode (indicator blinking).

# High Latency Answers

Assistant latency above 5 seconds usually means the model endpoint is cold or overloaded.
Quality engineers track p50 and p95 latency with Locust load tests and CloudWatch-style metrics.

# Wrong Warranty Answer

If the assistant says warranty is 5 years while the policy says 2 years, faithfulness fails and the case must be added to the golden regression set.

# Empty Responses

Null or empty chatbot responses in logs should be flagged by SQL validation queries.
Count conversations where response is NULL or latency exceeds 5 seconds.
