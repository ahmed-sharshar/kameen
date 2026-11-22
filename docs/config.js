/* Where the Kameen server lives. Local pages talk to a local server; everything else talks to the hosted one.
   HOSTED_API is the Render web service created from render.yaml. The access code is sent to whatever host
   is named here, so change it only to an address you own. */
const HOSTED_API = 'https://kameen-y4l2.onrender.com';
const API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1') ? 'http://localhost:8000' : HOSTED_API;
