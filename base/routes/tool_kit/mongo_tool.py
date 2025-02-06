from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId


def store_image_in_mongodb(image_file, email):
    """
    Stores the uploaded image into MongoDB using GridFS.
    :param image_file: The uploaded image file object.
    :param email: The email of the user (used as metadata for the image).
    :return: The MongoDB ObjectId of the stored image as a string.
    """
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb+srv://ciddarth:applexc@cluster0.mg1di.mongodb.net")
        db = client["AcuitySchedulingDjango"]

        # Initialize GridFS
        fs = gridfs.GridFS(db, collection="images")

        # Store the image in GridFS
        image_id = fs.put(
            image_file.read(),
            filename=image_file.name,
            content_type=image_file.content_type,
            metadata={"email": email}
        )

        return str(image_id)  # Return ObjectId as a string
    except Exception as e:
        raise Exception(f"Error storing image in MongoDB: {str(e)}")

def get_image_from_mongodb(image_id):
    """
    Retrieves the image content from MongoDB using GridFS.
    :param image_id: The ID of the image in MongoDB (as a string).
    :return: The image content in binary format.
    """
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb+srv://ciddarth:applexc@cluster0.mg1di.mongodb.net")
        db = client["AcuitySchedulingDjango"]

        # Initialize GridFS
        fs = gridfs.GridFS(db, collection="images")

        # Convert string image_id to ObjectId
        object_id = ObjectId(image_id)

        # Retrieve the image by ID
        image_data = fs.get(object_id)
        return image_data.read()
    except Exception as e:
        raise Exception(f"Error retrieving image from MongoDB: {str(e)}")