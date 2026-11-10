import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AppLayout from './AppLayout';

describe('AppLayout', () => {
  it('헤더의 로고·로그인 버튼과 푸터의 이용약관 링크를 렌더링한다', () => {
    render(
      <MemoryRouter>
        <AppLayout />
      </MemoryRouter>,
    );

    const header = screen.getByRole('banner');
    expect(within(header).getByText('TP')).toBeInTheDocument();
    expect(within(header).getByRole('button', { name: '로그인' })).toBeInTheDocument();

    const footer = screen.getByRole('contentinfo');
    expect(within(footer).getByRole('link', { name: '이용약관' })).toBeInTheDocument();
  });
});
