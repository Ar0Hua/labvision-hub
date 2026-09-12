package com.yupi.yupicture.application.agent;
import java.time.*;
import java.util.*;
import java.util.regex.*;
import com.yupi.yupicture.infrastructure.exception.*;

public class AgentStatisticsWindow {
    public java.util.Date start;
    public java.util.Date end;
    public Long uploaderId;
    public String startDate;
    public String endDate;
    public boolean active() { return start!=null || end!=null || uploaderId!=null; }
    public static AgentStatisticsWindow parse(String query, LocalDate today) {
        AgentStatisticsWindow filter=new AgentStatisticsWindow();
        if (query==null) return filter;
        Matcher dates=Pattern.compile("\\d{4}-\\d{2}-\\d{2}").matcher(query);
        List<LocalDate> found=new ArrayList<>();
        try {
            while(dates.find()) found.add(LocalDate.parse(dates.group()));
            if (found.size()>2) throw new IllegalArgumentException();
            LocalDate first=null,last=null;
            if(found.size()==2) { first=found.get(0); last=found.get(1); }
            else if(found.size()==1) { first=found.get(0); }
            else {
                Matcher recent=Pattern.compile("(?:最近|近)([1-9][0-9]?|一|二|两|三|四|五|六|七|八|九|十)(天|个月|月)").matcher(query);
                if(recent.find()) {
                    String number=recent.group(1);
                    int n="两".equals(number)?2:("一二三四五六七八九十".contains(number)
                            ?"一二三四五六七八九十".indexOf(number)+1:Integer.parseInt(number));
                    last=today;
                    first="天".equals(recent.group(2))?today.minusDays(n-1):today.minusMonths(n);
                }
            }
            if(first!=null && (first.getYear()<1970 || first.getYear()>2100
                    || last!=null && (last.isBefore(first)||last.getYear()>2100))) throw new IllegalArgumentException();
            ZoneId zone=ZoneId.of("Asia/Shanghai");
            if(first!=null) { filter.startDate=first.toString(); filter.start=Date.from(first.atStartOfDay(zone).toInstant()); }
            if(last!=null) { filter.endDate=last.toString(); filter.end=Date.from(last.plusDays(1).atStartOfDay(zone).toInstant()); }
            Matcher uploader=Pattern.compile("上传人(?:ID|id)?[：:\\s]*(\\d+)").matcher(query);
            if(uploader.find()) { filter.uploaderId=Long.valueOf(uploader.group(1)); if(filter.uploaderId<=0) throw new IllegalArgumentException(); }
            return filter;
        } catch(RuntimeException e) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR,"统计日期或上传人条件无效");
        }
    }
}
