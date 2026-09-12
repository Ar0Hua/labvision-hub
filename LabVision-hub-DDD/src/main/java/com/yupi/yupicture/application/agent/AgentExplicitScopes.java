package com.yupi.yupicture.application.agent;
import java.util.*;
import java.util.regex.*;
import com.yupi.yupicture.infrastructure.exception.*;

public class AgentExplicitScopes {
    public static List<Long> comparison(String query) {
        if(query==null || !query.contains("比较空间")) return Collections.emptyList();
        Matcher section=Pattern.compile("比较空间\\s*([0-9\\s,，、和与空间:：]+)").matcher(query);
        if(!section.find()) throw new BusinessException(ErrorCode.PARAMS_ERROR,"请明确指定 2 至 5 个空间 ID");
        Set<Long> ids=new LinkedHashSet<>();
        Matcher numbers=Pattern.compile("[0-9]+").matcher(section.group(1));
        try {
            while(numbers.find()) { long id=Long.parseLong(numbers.group()); if(id<=0) throw new IllegalArgumentException(); ids.add(id); }
        } catch(RuntimeException e) { throw new BusinessException(ErrorCode.PARAMS_ERROR,"空间 ID 无效"); }
        if(ids.size()<2 || ids.size()>5) throw new BusinessException(ErrorCode.PARAMS_ERROR,"请选择 2 至 5 个空间");
        return new ArrayList<>(ids);
    }
}
