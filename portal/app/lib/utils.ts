import { core } from "./core/client";

export const getDraft = async () => {
  const { data, error, response } = await core.GET("/draft");
  const status = response.status;

  if (error) {
    console.error("fetch draft failed with status ", status);
    return null;
  }

  const lastModified = response.headers.get("Last-Modified");

  return { draft: data, lastModified };
};

export const getVersions = async () => {
  const { data, error, response } = await core.GET("/versions");
  const status = response.status;

  if (error) {
    console.error("fetch versions failed with status ", status);
    return null;
  }

  return data;
};

export const getGrants = async () => {
  const { data, error, response } = await core.GET("/grants");
  const status = response.status;

  if (error) {
    console.error("fetch grants failed with status ", status);
    return null;
  }

  return data;
};
