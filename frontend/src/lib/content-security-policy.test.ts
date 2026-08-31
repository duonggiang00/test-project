import { createContentSecurityPolicy } from './content-security-policy';

const directives = (policy: string) => new Map(
  policy
    .split(';')
    .map((directive) => directive.trim())
    .filter(Boolean)
    .map((directive) => {
      const [name, ...values] = directive.split(/\s+/);
      return [name, values] as const;
    }),
);

describe('createContentSecurityPolicy', () => {
  it('limits the production browser to same-origin application dependencies', () => {
    const policy = createContentSecurityPolicy(false);
    const parsed = directives(policy);

    expect(parsed.get('script-src')).toEqual(["'self'", "'unsafe-inline'"]);
    expect(parsed.get('style-src')).toEqual(["'self'", "'unsafe-inline'"]);
    expect(parsed.get('img-src')).toEqual(["'self'", 'blob:', 'data:']);
    expect(parsed.get('font-src')).toEqual(["'self'", 'data:']);
    expect(parsed.get('connect-src')).toEqual(["'self'"]);
    expect(parsed.get('object-src')).toEqual(["'none'"]);
    expect(parsed.get('base-uri')).toEqual(["'self'"]);
    expect(parsed.get('form-action')).toEqual(["'self'"]);
    expect(parsed.get('frame-ancestors')).toEqual(["'self'"]);
    expect(policy).not.toContain("'unsafe-eval'");
    expect(policy).not.toContain('fonts.googleapis.com');
    expect(policy).not.toContain('fonts.gstatic.com');
    expect(policy).not.toContain('openrouter.ai');
    expect(policy).not.toContain('127.0.0.1:8000');
    expect(policy).not.toContain('https://*');
  });

  it('retains unsafe-eval only for the React development runtime', () => {
    const parsed = directives(createContentSecurityPolicy(true));

    expect(parsed.get('script-src')).toEqual([
      "'self'",
      "'unsafe-inline'",
      "'unsafe-eval'",
    ]);
  });
});
