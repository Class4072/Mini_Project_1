package com.trip.api

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.autoconfigure.domain.EntityScan
import org.springframework.boot.context.properties.ConfigurationPropertiesScan
import org.springframework.boot.runApplication
import org.springframework.data.jpa.repository.config.EnableJpaRepositories

@SpringBootApplication(scanBasePackages = ["com.trip"])
@EntityScan("com.trip.core")
@EnableJpaRepositories("com.trip.core")
@ConfigurationPropertiesScan
class TourApiApplication

fun main(args: Array<String>) {
    runApplication<TourApiApplication>(*args)
}
