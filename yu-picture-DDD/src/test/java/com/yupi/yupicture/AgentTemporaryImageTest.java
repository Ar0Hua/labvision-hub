package com.yupi.yupicture;

import com.yupi.yupicture.application.agent.AgentTemporaryImageService;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class AgentTemporaryImageTest {
    @Test void reencodesAndBoundsPixels() throws Exception {
        BufferedImage image=new BufferedImage(2048,32,BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        ImageIO.write(image,"png",bytes);
        Map<String,Object> normalized=AgentTemporaryImageService.normalize(bytes.toByteArray(),"sample.png","image/png");
        assertEquals(1024,normalized.get("width"));
        assertEquals(16,normalized.get("height"));
        assertTrue(normalized.get("dataUrl").toString().startsWith("data:image/jpeg;base64,"));
        assertFalse(normalized.containsKey("pictureId"));
        assertThrows(BusinessException.class,()->AgentTemporaryImageService.normalize(bytes.toByteArray(),"sample.jpg","image/jpeg"));
        assertThrows(BusinessException.class,()->AgentTemporaryImageService.normalize(bytes.toByteArray(),"sample.png","image/svg+xml"));
    }
    @Test void rejectsInvalidAndOversizeFiles() {
        assertThrows(BusinessException.class,()->AgentTemporaryImageService.normalize(new byte[5*1024*1024+1],"x.png","image/png"));
        assertThrows(BusinessException.class,()->AgentTemporaryImageService.normalize(new byte[]{1,2,3},"x.png","image/png"));
        assertThrows(BusinessException.class,()->AgentTemporaryImageService.normalize("<svg/>".getBytes(),"x.svg","image/svg+xml"));
    }
}
