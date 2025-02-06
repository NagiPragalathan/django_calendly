import gridfs
from pymongo import MongoClient

def store_image_in_mongodb(image_path, db_name="AcuitySchedulingDjango", collection_name="images"):
    """
    Stores an image into MongoDB using GridFS.
    
    :param image_path: Path to the image file.
    :param db_name: Name of the MongoDB database.
    :param collection_name: Name of the GridFS collection.
    """
    try:
        # Connect to MongoDB using your connection string
        client = MongoClient("mongodb+srv://ciddarth:applexc@cluster0.mg1di.mongodb.net")
        db = client[db_name]

        # Initialize GridFS
        fs = gridfs.GridFS(db, collection=collection_name)

        # Open the image file
        with open(image_path, "rb") as f:
            # Store the image in GridFS
            image_id = fs.put(f, filename=image_path.split("/")[-1])
        
        print(f"Image stored successfully with ID: {image_id}")
        return image_id
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def retrieve_image_from_mongodb(image_id, save_path, db_name="AcuitySchedulingDjango", collection_name="images"):
    """
    Retrieves an image from MongoDB using GridFS and saves it to disk.
    
    :param image_id: ID of the image to retrieve.
    :param save_path: Path to save the retrieved image.
    :param db_name: Name of the MongoDB database.
    :param collection_name: Name of the GridFS collection.
    """
    try:
        # Connect to MongoDB using your connection string
        client = MongoClient("mongodb+srv://ciddarth:applexc@cluster0.mg1di.mongodb.net")
        db = client[db_name]

        # Initialize GridFS
        fs = gridfs.GridFS(db, collection=collection_name)

        # Retrieve the image
        image_data = fs.get(image_id)

        # Save the image to disk
        with open(save_path, "wb") as f:
            f.write(image_data.read())
        
        print(f"Image retrieved and saved to {save_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
retrieve_image_from_mongodb('6794963f35011815ff9adaa9', "/")


# Example usage
# image_id = store_image_in_mongodb(r"C:\Users\Admin\Documents\Work\susanoox\django_acuity_scheduling\Screenshot 2024-10-06 055149.png")
