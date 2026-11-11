package com.trip.api.common

class BusinessException(val errorCode: ErrorCode, override val message: String = errorCode.message) :
    RuntimeException(message)
