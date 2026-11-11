package com.trip.api.common

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.MDC
import org.springframework.core.Ordered
import org.springframework.core.annotation.Order
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter
import java.util.UUID

/**
 * 요청마다 traceId를 MDC에 넣어 로그에 [req_id=...]로 찍는다 (BACKEND.md 8장).
 * 앞단(Nginx 등)이 X-Request-Id를 주면 그 값을 이어 쓰고, 응답 헤더 X-Trace-Id로 돌려준다.
 * 비동기 처리(코루틴 컨트롤러)가 끝나고 다시 들어오는 디스패치에서도 같은 값을 쓴다.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class TraceIdFilter : OncePerRequestFilter() {
    override fun shouldNotFilterAsyncDispatch(): Boolean = false

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain,
    ) {
        val traceId =
            request.getAttribute(TRACE_ID_ATTRIBUTE) as? String
                ?: request.getHeader(REQUEST_ID_HEADER)?.takeIf { SAFE_ID.matches(it) }
                ?: newTraceId()
        if (!isAsyncDispatch(request)) {
            request.setAttribute(TRACE_ID_ATTRIBUTE, traceId)
            response.setHeader(TRACE_ID_HEADER, traceId)
        }
        MDC.put(MDC_KEY, traceId)
        try {
            filterChain.doFilter(request, response)
        } finally {
            MDC.remove(MDC_KEY)
        }
    }

    private fun newTraceId(): String = UUID.randomUUID().toString().replace("-", "").take(16)

    companion object {
        const val MDC_KEY = "traceId"
        const val TRACE_ID_HEADER = "X-Trace-Id"
        private const val REQUEST_ID_HEADER = "X-Request-Id"
        private val TRACE_ID_ATTRIBUTE = TraceIdFilter::class.java.name + ".traceId"
        private val SAFE_ID = Regex("^[A-Za-z0-9-]{1,64}$")
    }
}
