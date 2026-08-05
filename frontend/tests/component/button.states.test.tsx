import { fireEvent, render, screen } from '@testing-library/react';

import { Button } from '@/components/ui/button';


describe('Button interaction states', () => {
  test('disabled state blocks pointer activation', () => {
    const onClick = jest.fn();
    render(
      <Button disabled onClick={onClick}>
        Save
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  test('enabled state exposes native keyboard-focusable button semantics', () => {
    render(<Button>Continue</Button>);

    const button = screen.getByRole('button', { name: 'Continue' });
    expect(button.tagName).toBe('BUTTON');
    button.focus();
    expect(button).toHaveFocus();
  });
});
