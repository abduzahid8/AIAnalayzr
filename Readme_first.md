Vigil is a risk-intelligence product built on a FastAPI backend and a React Native / Expo frontend.

Product direction:
- `vigil/client` is the primary product surface for both web and mobile.
- Backend quality is a first-order priority. Frontend work must not weaken API correctness, session integrity, or system trust.
- `vigil/static/index.html` and `vigil/mobile` are legacy paths and should not be the center of new product work.

Core product outcome:
- company profile intake
- multi-agent risk analysis
- 0-100 risk score with tier
- top risks, actions, and 30-day playbook
- advisor chat grounded in the current report