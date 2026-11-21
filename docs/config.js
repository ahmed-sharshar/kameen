/* Where the Kameen server lives. Local pages talk to a local server; everything else talks to the hosted one.
   HOSTED_API is a placeholder until the Render service exists. Replace it with that service's real address,
   and never with a guess: the access code is sent to whatever host is named here. */
const HOSTED_API = 'https://kameen-server-not-deployed.invalid';
const API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1') ? 'http://localhost:8000' : HOSTED_API;
