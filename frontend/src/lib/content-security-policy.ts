const commonDirectives = [
  "default-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self'",
];

export const createContentSecurityPolicy = (isDevelopment: boolean): string => {
  const scriptSources = ["'self'", "'unsafe-inline'"];
  if (isDevelopment) scriptSources.push("'unsafe-eval'");

  return [
    commonDirectives[0],
    `script-src ${scriptSources.join(' ')}`,
    ...commonDirectives.slice(1),
  ]
    .map((directive) => `${directive};`)
    .join(' ');
};
