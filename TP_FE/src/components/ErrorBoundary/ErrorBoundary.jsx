import { Component } from "react";
import { logger } from "../../utils/logger";
import Button from "../Button/Button";
import styles from "./ErrorBoundary.module.css";

// 오류 시 기본으로 보여주는 화면. 지도처럼 문구만 바꿔 쓰려면 fallback 에서 이 컴포넌트를 쓴다.
export function ErrorFallback({ message = "화면을 불러오지 못했어요", onRetry, className }) {
  return (
    <div role="alert" className={[styles.fallback, className].filter(Boolean).join(" ")}>
      <p className={styles.message}>{message}</p>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        다시 시도
      </Button>
    </div>
  );
}

function hasChanged(prevKeys = [], nextKeys = []) {
  return (
    prevKeys.length !== nextKeys.length ||
    prevKeys.some((key, index) => !Object.is(key, nextKeys[index]))
  );
}

// 렌더링 중 오류만 잡는다. (이벤트 핸들러·비동기 오류는 각 컴포넌트가 직접 처리)
// React 의 오류 경계는 클래스 컴포넌트로만 만들 수 있다.
// - fallback: 오류 시 보여줄 내용. 함수면 (reset) => 내용 으로 호출한다. 없으면 ErrorFallback.
// - resetKeys: 배열 값 중 하나라도 바뀌면 오류 상태를 초기화한다. (예: [location.pathname])
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    logger.error("[ErrorBoundary] 렌더링 오류", error, info.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && hasChanged(prevProps.resetKeys, this.props.resetKeys)) {
      this.reset();
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;

    const { fallback } = this.props;
    if (typeof fallback === "function") return fallback(this.reset);
    if (fallback !== undefined) return fallback;
    return <ErrorFallback onRetry={this.reset} />;
  }
}
