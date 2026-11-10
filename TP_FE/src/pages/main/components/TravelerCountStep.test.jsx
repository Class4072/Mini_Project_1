import { fireEvent, render, screen } from '@testing-library/react';
import TravelerCountStep from './TravelerCountStep';

describe('TravelerCountStep', () => {
  it('인원 상한이 있으면 그 값에서 늘리기 버튼이 비활성이다', () => {
    const onChange = jest.fn();
    render(<TravelerCountStep value={8} onChange={onChange} maxTravelers={8} />);
    expect(screen.getByRole('button', { name: '인원 늘리기' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '인원 줄이기' }));
    expect(onChange).toHaveBeenCalledWith(7);
  });

  it('6명 미만이면 프리셋 버튼만 선택 상태이고 조절 버튼은 비활성이다', () => {
    render(<TravelerCountStep value={4} onChange={jest.fn()} maxTravelers={null} />);
    expect(screen.getByRole('button', { name: '4명' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '6명 이상' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
    expect(screen.getByRole('button', { name: '인원 늘리기' })).toBeDisabled();
  });
});
