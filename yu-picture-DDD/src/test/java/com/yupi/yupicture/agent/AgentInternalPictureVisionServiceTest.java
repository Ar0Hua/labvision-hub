package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.api.CosManager;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentInternalPictureVisionServiceTest {
    @Test void signsThumbnailOnlyAfterTaskAndPictureAuthorization() {
        AgentInternalPictureVisionService service = service();
        AgentInternalTaskService internal = field(service, "internalTasks");
        AgentPictureService authorized = field(service, "authorizedPictures");
        PictureRepository pictures = field(service, "pictures");
        CosManager cos = field(service, "cos");
        when(internal.context("Bearer token", "task")).thenReturn(context());
        Map<String,Object> metadata = new LinkedHashMap<>();
        metadata.put("pictureId", "12"); metadata.put("name", "实验图");
        when(authorized.details(eq("conversation"), eq(Collections.singletonList(12L)), any()))
                .thenReturn(Collections.singletonList(metadata));
        Picture picture = new Picture(); picture.setId(12L); picture.setIsDelete(0);
        picture.setUrl("https://cos.example/original.png");
        picture.setThumbnailUrl("https://cos.example/thumbnail.png");
        when(pictures.getById(12L)).thenReturn(picture);
        when(cos.generatePresignedGetUrl(picture.getThumbnailUrl(), 120))
                .thenReturn("https://signed.example/thumbnail.png?token=short");

        List<Map<String,Object>> result = service.inputs(
                "Bearer token", "task", Collections.singletonList(12L));

        assertEquals("https://signed.example/thumbnail.png?token=short", result.get(0).get("temporaryUrl"));
        assertEquals(120, result.get(0).get("expiresInSeconds"));
        verify(cos, never()).generatePresignedGetUrl(picture.getUrl(), 120);
    }

    @Test void rejectsOversizedVisionBatchBeforeAnyAuthorization() {
        AgentInternalPictureVisionService service = service();
        AgentInternalTaskService internal = field(service, "internalTasks");
        assertThrows(BusinessException.class, () -> service.inputs(
                "Bearer token", "task", Arrays.asList(1L,2L,3L,4L,5L,6L,7L,8L,9L)));
        verifyNoInteractions(internal);
    }

    private static AgentInternalPictureVisionService service() {
        AgentInternalPictureVisionService service = new AgentInternalPictureVisionService();
        ReflectionTestUtils.setField(service, "internalTasks", mock(AgentInternalTaskService.class));
        ReflectionTestUtils.setField(service, "authorizedPictures", mock(AgentPictureService.class));
        ReflectionTestUtils.setField(service, "pictures", mock(PictureRepository.class));
        ReflectionTestUtils.setField(service, "cos", mock(CosManager.class));
        return service;
    }
    private static Map<String,Object> context() {
        Map<String,Object> value = new HashMap<>();
        value.put("userId", "7"); value.put("conversationId", "conversation");
        return value;
    }
    @SuppressWarnings("unchecked")
    private static <T> T field(Object target, String name) {
        return (T) ReflectionTestUtils.getField(target, name);
    }
}
