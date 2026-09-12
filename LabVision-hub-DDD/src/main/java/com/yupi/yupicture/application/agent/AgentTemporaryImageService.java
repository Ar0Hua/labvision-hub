package com.yupi.yupicture.application.agent;

import cn.hutool.json.JSONUtil;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import org.springframework.stereotype.Service;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.web.multipart.MultipartFile;
import javax.annotation.Resource;
import javax.imageio.*;
import javax.imageio.stream.MemoryCacheImageInputStream;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
public class AgentTemporaryImageService {
    public static final int TTL_SECONDS=900;
    @Resource private AgentConversationService conversations;
    @Resource private StringRedisTemplate redis;
    private static final DefaultRedisScript<Long> QUOTA=new DefaultRedisScript<>(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],900) end; return n",Long.class);

    public Map<String,Object> upload(String conversationId,User user,MultipartFile file) {
        conversations.requireOwner(conversationId,user);
        if(file==null || file.isEmpty() || file.getSize()>5*1024*1024) invalid();
        Long count=redis.execute(QUOTA,Collections.singletonList("agent:temp:quota:"+user.getId()));
        if(count==null || count>5) throw new BusinessException(ErrorCode.OPERATION_ERROR,"每15分钟最多上传5张临时图片");
        Map<String,Object> value;
        try { value=normalize(file.getBytes(),file.getOriginalFilename(),file.getContentType()); }
        catch(IOException e) { throw new BusinessException(ErrorCode.PARAMS_ERROR,"临时图片解码失败"); }
        String id=UUID.randomUUID().toString();
        value.put("temporaryId",id);
        redis.opsForValue().set(key(conversationId,user,id),JSONUtil.toJsonStr(value),TTL_SECONDS,TimeUnit.SECONDS);
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("temporaryId",id);result.put("expiresInSeconds",TTL_SECONDS);
        result.put("width",value.get("width"));result.put("height",value.get("height"));
        return result;
    }

    public Map<String,Object> load(String conversationId,User user,String id) {
        conversations.requireOwner(conversationId,user);
        String value=redis.opsForValue().get(key(conversationId,user,id));
        if(value==null) throw new BusinessException(ErrorCode.PARAMS_ERROR,"临时图片已过期或不可访问，请重新上传");
        return new LinkedHashMap<>(JSONUtil.parseObj(value));
    }

    public void remove(String conversationId,User user,String id) {
        conversations.requireOwner(conversationId,user);
        redis.delete(key(conversationId,user,id));
    }

    private String key(String conversationId,User user,String id) {
        if(id==null || !id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) invalid();
        return "agent:temp:image:"+user.getId()+":"+conversationId+":"+id;
    }

    /** Re-encode to strip metadata/polyglot tails; validate dimensions before pixel allocation. */
    public static Map<String,Object> normalize(byte[] bytes,String filename,String mime) throws IOException {
        if(bytes==null || bytes.length==0 || bytes.length>5*1024*1024 || filename==null) invalid();
        String name=filename.toLowerCase(Locale.ROOT);
        boolean png=name.endsWith(".png") && "image/png".equals(mime);
        boolean jpeg=(name.endsWith(".jpg") || name.endsWith(".jpeg")) && "image/jpeg".equals(mime);
        if(!png && !jpeg) invalid();
        if(png && (bytes.length<8 || bytes[0]!=(byte)137 || bytes[1]!=80 || bytes[2]!=78 || bytes[3]!=71)) invalid();
        if(jpeg && (bytes.length<3 || bytes[0]!=(byte)255 || bytes[1]!=(byte)216 || bytes[2]!=(byte)255)) invalid();
        try(MemoryCacheImageInputStream input=new MemoryCacheImageInputStream(new ByteArrayInputStream(bytes))) {
            Iterator<ImageReader> readers=ImageIO.getImageReaders(input);
            if(!readers.hasNext()) invalid();
            ImageReader reader=readers.next();
            try {
                if(!(png?"png":"JPEG").equalsIgnoreCase(reader.getFormatName())) invalid();
                reader.setInput(input,true,true);
                int width=reader.getWidth(0),height=reader.getHeight(0);
                if(width<1 || height<1 || width>10000 || height>10000 || (long)width*height>16000000) invalid();
                BufferedImage decoded=reader.read(0);
                double scale=Math.min(1d,1024d/Math.max(width,height));
                int w=Math.max(1,(int)(width*scale)),h=Math.max(1,(int)(height*scale));
                BufferedImage resized=new BufferedImage(w,h,BufferedImage.TYPE_INT_RGB);
                Graphics2D graphics=resized.createGraphics();
                try { graphics.setColor(Color.WHITE);graphics.fillRect(0,0,w,h);graphics.drawImage(decoded,0,0,w,h,null); }
                finally { graphics.dispose();decoded.flush(); }
                ByteArrayOutputStream output=new ByteArrayOutputStream();
                if(!ImageIO.write(resized,"jpeg",output)) invalid();
                resized.flush();
                if(output.size()>1024*1024) invalid();
                Map<String,Object> value=new LinkedHashMap<>();value.put("width",w);value.put("height",h);
                value.put("dataUrl","data:image/jpeg;base64,"+Base64.getEncoder().encodeToString(output.toByteArray()));
                return value;
            } finally { reader.dispose(); }
        }
    }

    private static void invalid() { throw new BusinessException(ErrorCode.PARAMS_ERROR,"仅支持5MB内的PNG/JPEG，尺寸与文件内容必须有效"); }
}
