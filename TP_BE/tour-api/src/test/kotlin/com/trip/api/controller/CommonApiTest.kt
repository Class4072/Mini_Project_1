package com.trip.api.controller

import com.trip.api.support.IntegrationTestSupport
import org.junit.jupiter.api.Test
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.header
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status

class CommonApiTest : IntegrationTestSupport() {
    @Test
    fun `없는 주소도 ApiResponse 형식의 404로 답한다`() {
        perform(get("/api/v1/nothing"))
            .andExpect(status().isNotFound)
            .andExpect(jsonPath("$.success").value(false))
            .andExpect(jsonPath("$.code").value("NOT_FOUND"))
            .andExpect(header().exists("X-Trace-Id"))
    }

    @Test
    fun `잘못된 메서드와 경로 변수 형식은 405와 400이다`() {
        perform(delete("/api/v1/map/places"))
            .andExpect(status().isMethodNotAllowed)
            .andExpect(jsonPath("$.code").value("METHOD_NOT_ALLOWED"))
        perform(get("/api/v1/trips/abc"))
            .andExpect(status().isBadRequest)
            .andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
    }

    @Test
    fun `앞단이 준 X-Request-Id를 traceId로 이어 쓰고 이상한 값은 새로 만든다`() {
        perform(get("/api/v1/nothing").header("X-Request-Id", "nginx-abc-123"))
            .andExpect(header().string("X-Trace-Id", "nginx-abc-123"))
        perform(get("/api/v1/nothing").header("X-Request-Id", "bad id\nINJECTED"))
            .andExpect(header().string("X-Trace-Id", org.hamcrest.Matchers.matchesPattern("^[0-9a-f]{16}$")))
    }
}
