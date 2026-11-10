import { fireEvent, render, screen } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  it('클릭하면 onClick 을 호출한다', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>확인</Button>);

    fireEvent.click(screen.getByRole('button', { name: '확인' }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('disabled 일 때 클릭해도 onClick 을 호출하지 않는다', () => {
    const handleClick = jest.fn();
    render(
      <Button disabled onClick={handleClick}>
        확인
      </Button>,
    );

    const button = screen.getByRole('button', { name: '확인' });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });
});
