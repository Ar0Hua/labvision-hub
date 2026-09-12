package com.yupi.yupicture.infrastructure.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

@Configuration
public class AgentHttpConfig {
    @Bean("agentRestTemplate")
    public RestTemplate agentRestTemplate(
            RestTemplateBuilder builder,
            @Value("${agent.service.connect-timeout-ms:2000}") long connectTimeoutMs,
            @Value("${agent.service.read-timeout-ms:5000}") long readTimeoutMs) {
        return builder
                .setConnectTimeout(Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(Duration.ofMillis(readTimeoutMs))
                .build();
    }
}
