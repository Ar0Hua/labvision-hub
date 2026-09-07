<template>
    <div id="addPicturePage">
        <h2 style="margin-bottom: 16px">
            {{ route.query?.id ? '修改图片' : '创建图片' }}
        </h2>
        <a-typography-paragraph v-if="spaceId" type="secondary">
            保存至空间：<a :href="`/space/${spaceId}`" target="_blank">{{ spaceId }}</a>
        </a-typography-paragraph>
        <!-- 选择上传方式 -->
        <a-tabs v-model:activeKey="uploadType">
            <a-tab-pane key="file" tab="文件上传">
                <!-- 图片上传组件 -->
                <PictureUpload :picture="picture" :spaceId="spaceId" :onSuccess="onSuccess" />
            </a-tab-pane>
            <a-tab-pane key="url" tab="URL 上传" force-render>
                <!-- URL 图片上传组件 -->
                <UrlPictureUpload :picture="picture" :spaceId="spaceId" :onSuccess="onSuccess" />
            </a-tab-pane>
        </a-tabs>
        <!-- 图片编辑 -->
        <div v-if="picture" class="edit-bar">
            <a-space size="middle">
                <a-button :icon="h(EditOutlined)" @click="doEditPicture">编辑图片</a-button>
                <a-button type="primary" :icon="h(FullscreenOutlined)" @click="doImagePainting">
                    AI 扩图
                </a-button>
            </a-space>
            <ImageCropper ref="imageCropperRef" :imageUrl="picture?.url" :picture="picture" :spaceId="spaceId"
                :space="space" :onSuccess="onCropSuccess" />
            <ImageOutPainting ref="imageOutPaintingRef" :picture="picture" :spaceId="spaceId"
                :onSuccess="onImageOutPaintingSuccess" />
        </div>
        <!-- 图片信息表单 -->
        <!-- 搜索表单 -->
        <a-form name="pictureForm" layout="vertical" :model="pictureForm" @finish="handleSubmit">
            <a-form-item name="name" label="名称">
                <a-input v-model:value="pictureForm.name" placeholder="请输入名称" allow-clear />
            </a-form-item>
            <a-form-item name="introduction" label="简介">
                <a-textarea v-model:value="pictureForm.introduction" placeholder="请输入简介"
                    :auto-size="{ minRows: 2, maxRows: 5 }" allow-clear />
            </a-form-item>
            <a-form-item name="category" label="分类">
                <a-auto-complete v-model:value="pictureForm.category" placeholder="请输入分类" :options="categoryOptions"
                    allow-clear />
            </a-form-item>
            <a-form-item name="tags" label="标签">
                <a-select v-model:value="pictureForm.tags" mode="tags" placeholder="请输入标签" :options="tagOptions"
                    allow-clear />
            </a-form-item>
            <a-form-item name="reviewStatus" label="审核状态">
                <a-select v-model:value="pictureForm.reviewStatus" placeholder="请选择审核状态"
                    :options="PIC_REVIEW_STATUS_OPTIONS" allow-clear />
            </a-form-item>
            <a-form-item>
                <a-button type="primary" html-type="submit" style="width: 100%">创建</a-button>
            </a-form-item>
        </a-form>
    </div>
</template>

<script setup lang="ts">
import PictureUpload from '@/components/PictureUpload.vue'
import UrlPictureUpload from '@/components/UrlPictureUpload.vue'
import { onMounted, ref, reactive, computed, h, watchEffect } from 'vue'
import { message } from 'ant-design-vue'
import { editPictureUsingPost, getPictureVoByIdUsingGet } from '@/api/pictureController'
import { useRoute, useRouter } from 'vue-router'
import { PIC_REVIEW_STATUS_OPTIONS } from '@/constants/picture'
import { EditOutlined, FullscreenOutlined } from '@ant-design/icons-vue'
import ImageCropper from '@/components/ImageCropper.vue'
import { getSpaceVoByIdUsingGet } from '@/api/spaceController.ts'
import ImageOutPainting from '@/components/ImageOutPainting.vue'
import { PICTURE_CATEGORY_KEYWORDS, PICTURE_TAG_KEYWORDS, toSelectOptions } from '@/constants/pictureKeywords'

const router = useRouter()
const route = useRoute()

const picture = ref<API.PictureVO>()

const pictureForm = reactive<API.PictureEditRequest>({})
const uploadType = ref<'file' | 'url'>('file')
// 空间 id
const spaceId = computed(() => {
    return route.query?.spaceId
})

/**
 * 图片上传成功回调
 * @param newPicture 上传成功的图片信息
 */
const onSuccess = (newPicture: API.PictureVO) => {
    picture.value = newPicture;
    pictureForm.name = newPicture.name
}


/**
 * 提交表单
 * @param values
 */
const handleSubmit = async (values: any) => {
    const pictureId = picture.value?.id
    if (!pictureId) {
        return
    }
    const res = await editPictureUsingPost({
        id: pictureId,
        ...values
    })
    // 操作成功
    if (res.data.code === 0 && res.data.data) {
        message.success('创建成功')
        //跳转图片详情页
        router.push({ path: `/picture/${pictureId}`, })

    } else {
        message.error('创建失败，' + res.data.message)
    }
}

const categoryOptions = toSelectOptions(PICTURE_CATEGORY_KEYWORDS)
const tagOptions = toSelectOptions(PICTURE_TAG_KEYWORDS)

// 获取老数据
const getOldPicture = async () => {
    // 获取到 id
    const id = route.query?.id
    if (id) {
        const res = await getPictureVoByIdUsingGet({
            id,
        })
        if (res.data.code === 0 && res.data.data) {
            const data = res.data.data
            picture.value = data
            pictureForm.name = data.name
            pictureForm.introduction = data.introduction
            pictureForm.category = data.category
            pictureForm.tags = data.tags
        }
    }
}

onMounted(() => {
    getOldPicture()
})

// ----- 图片编辑器引用 ------
const imageCropperRef = ref()

// 编辑图片
const doEditPicture = async () => {
    imageCropperRef.value?.openModal()
}

// 编辑成功事件
const onCropSuccess = (newPicture: API.PictureVO) => {
    picture.value = newPicture
}

// ----- AI 扩图引用 -----
const imageOutPaintingRef = ref()

// 打开 AI 扩图弹窗
const doImagePainting = async () => {
    imageOutPaintingRef.value?.openModal()
}

// AI 扩图保存事件
const onImageOutPaintingSuccess = (newPicture: API.PictureVO) => {
    picture.value = newPicture
}

// 获取空间信息
const space = ref<API.SpaceVO>()

// 获取空间信息
const fetchSpace = async () => {
    // 获取数据
    if (spaceId.value) {
        const res = await getSpaceVoByIdUsingGet({
            id: spaceId.value,
        })
        if (res.data.code === 0 && res.data.data) {
            space.value = res.data.data
        }
    }
}

watchEffect(() => {
    fetchSpace()
})

</script>

<style scoped>
#addPicturePage {
    max-width: 720px;
    margin: 0 auto;
}

#addPicturePage .edit-bar {
    text-align: center;
    margin: 16px 0;
}
</style>
