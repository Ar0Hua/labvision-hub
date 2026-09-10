package com.yupi.yupicture.infrastructure.config;

import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import javax.servlet.*;
import javax.servlet.http.*;
import java.io.IOException;

/** Correlate signed callbacks without logging bodies, query text or bearer tokens. */
@Component
@lombok.extern.slf4j.Slf4j
public class AgentTraceFilter extends OncePerRequestFilter {
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain)
            throws ServletException,IOException {
        String parent=request.getHeader("traceparent");
        if(!request.getRequestURI().contains("/agent/internal/") || parent==null ||
                !parent.matches("00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]")) {
            chain.doFilter(request,response);return;
        }
        long start=System.nanoTime();
        try { chain.doFilter(request,response); }
        finally { log.info("agent_callback trace_id={} parent_span_id={} status={} duration_ms={}",
            parent.substring(3,35),parent.substring(36,52),response.getStatus(),(System.nanoTime()-start)/1000000); }
    }
}
