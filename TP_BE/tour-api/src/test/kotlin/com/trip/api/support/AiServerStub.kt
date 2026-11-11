package com.trip.api.support

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** 가짜 AI 서비스. 테스트마다 돌려줄 응답을 정하고, 백엔드가 보낸 요청을 꺼내 본다. */
object AiServerStub {
    private val server = MockWebServer()
    private val nextResponse = AtomicReference(noStub())
    private val requests = LinkedBlockingQueue<RecordedRequest>()

    init {
        server.dispatcher =
            object : Dispatcher() {
                override fun dispatch(request: RecordedRequest): MockResponse {
                    requests.add(request)
                    return nextResponse.get()
                }
            }
        server.start()
    }

    val baseUrl: String
        get() = server.url("/").toString().trimEnd('/')

    val requestCount: Int
        get() = requests.size

    fun respond(response: MockResponse) = nextResponse.set(response)

    fun respondJson(body: String) = respond(MockResponse().setHeader("Content-Type", "application/json").setBody(body))

    fun takeRequest(): RecordedRequest = requireNotNull(requests.poll(5, TimeUnit.SECONDS)) { "AI 서비스로 간 요청이 없습니다." }

    fun reset() {
        requests.clear()
        nextResponse.set(noStub())
    }

    private fun noStub() = MockResponse().setResponseCode(500).setBody("""{"detail":"테스트에서 응답을 정하지 않았습니다"}""")
}

/** AI 응답 JSON 만들기 (TP_AI API_SPEC.md 5.2 형식) */
object AiResponses {
    private val mapper = jacksonObjectMapper()

    fun schedule(vararg days: AiDay, tripName: String = "비 오는 부산 1박 2일"): String = mapper.writeValueAsString(
        mapOf(
            "tripName" to tripName,
            "weatherSummary" to "1일차는 비, 2일차는 맑음",
            "dailySchedules" to
                days.mapIndexed { index, day ->
                    mapOf(
                        "day" to index + 1,
                        "weatherCondition" to day.weather,
                        "places" to
                            day.stops.mapIndexed { step, stop ->
                                mapOf(
                                    "step" to step + 1,
                                    "placeId" to stop.placeId,
                                    "placeName" to "AI가 쓴 이름",
                                    "category" to "자연/산책",
                                    "startTime" to stop.start,
                                    "endTime" to stop.end,
                                    "stayTimeMinutes" to 60,
                                    "latitude" to 35.1,
                                    "longitude" to 129.1,
                                    "reason" to stop.reason,
                                    "distanceFromPrevKm" to 0.5,
                                )
                            },
                    )
                },
        ),
    )
}

data class AiDay(val weather: String, val stops: List<AiStop>)

data class AiStop(
    val placeId: Any,
    val start: String = "10:00",
    val end: String = "11:00",
    val reason: String = "추천 이유",
)
