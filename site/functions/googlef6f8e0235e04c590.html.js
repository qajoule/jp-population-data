export function onRequest({ request, env }) {
  // Pages serves the HTML asset directly at its extensionless path.
  const url = new URL(request.url);
  url.pathname = "/googlef6f8e0235e04c590";
  return env.ASSETS.fetch(new Request(url, request));
}
